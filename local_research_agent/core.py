from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeAlias


@dataclass(frozen=True)
class ToolCall:
    """A request to run one named, allow-listed tool."""

    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class Citation:
    """A file and line range that must be present in a read-tool observation."""

    path: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class FinalAnswer:
    text: str
    citations: tuple[Citation, ...] = ()


Action: TypeAlias = ToolCall | FinalAnswer


@dataclass(frozen=True)
class Observation:
    tool_name: str
    result: object | None = None
    error: str | None = None


@dataclass(frozen=True)
class AgentResult:
    answer: str
    observations: tuple[Observation, ...]
    stop_reason: str
    citations: tuple[Citation, ...] = ()


class Planner(Protocol):
    def choose_next_action(
        self,
        goal: str,
        observations: Sequence[Observation],
    ) -> Action: ...


class ToolError(Exception):
    """A safe, expected error caused by invalid tool input or unavailable data."""


class PlannerError(Exception):
    """A controlled planner/model failure that should stop the agent loop."""


ToolHandler = Callable[[dict[str, object]], object]


class ToolRegistry:
    """Executes only the tools explicitly registered by the application."""

    def __init__(self, handlers: dict[str, ToolHandler]) -> None:
        self._handlers = dict(handlers)

    @property
    def names(self) -> frozenset[str]:
        return frozenset(self._handlers)

    def execute(self, call: ToolCall) -> Observation:
        handler = self._handlers.get(call.name)
        if handler is None:
            return Observation(tool_name=call.name, error="Tool is not registered.")

        try:
            result = handler(call.arguments)
        except ToolError as error:
            return Observation(tool_name=call.name, error=str(error))

        return Observation(tool_name=call.name, result=result)


class ResearchAgent:
    """A bounded, evidence-first observe/act loop with citation enforcement."""

    def __init__(
        self,
        planner: Planner,
        tools: ToolRegistry,
        max_steps: int = 6,
    ) -> None:
        if not 1 <= max_steps <= 20:
            raise ValueError("max_steps must be between 1 and 20")
        self._planner = planner
        self._tools = tools
        self._max_steps = max_steps

    def run(self, goal: str) -> AgentResult:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal must not be empty")
        if len(goal) > 1000:
            raise ValueError("goal must be 1000 characters or fewer")

        observations: list[Observation] = []
        for _ in range(self._max_steps + 1):
            try:
                action = self._planner.choose_next_action(goal, tuple(observations))
            except PlannerError:
                return AgentResult(
                    answer="The planner could not complete this request. Please try again.",
                    observations=tuple(observations),
                    stop_reason="planner_error",
                    citations=self._citations_from_observations(observations),
                )

            if isinstance(action, FinalAnswer):
                return self._finish(action, observations)

            if not isinstance(action, ToolCall):
                return AgentResult(
                    answer="The planner returned an invalid action. No further action was taken.",
                    observations=tuple(observations),
                    stop_reason="invalid_action",
                    citations=self._citations_from_observations(observations),
                )

            if len(observations) >= self._max_steps:
                return AgentResult(
                    answer="Stopped safely: the maximum number of tool steps was reached.",
                    observations=tuple(observations),
                    stop_reason="max_steps",
                    citations=self._citations_from_observations(observations),
                )

            authorization_error = self._authorize_tool_call(action, observations)
            if authorization_error:
                observations.append(authorization_error)
            else:
                observations.append(self._tools.execute(action))

        return AgentResult(
            answer="Stopped safely: the maximum number of tool steps was reached.",
            observations=tuple(observations),
            stop_reason="max_steps",
            citations=self._citations_from_observations(observations),
        )

    def _finish(
        self,
        action: FinalAnswer,
        observations: Sequence[Observation],
    ) -> AgentResult:
        successful_searches = [
            item
            for item in observations
            if item.tool_name == "search_documents" and not item.error
        ]
        if not successful_searches:
            return AgentResult(
                answer="No approved local document was searched, so no research answer was produced.",
                observations=tuple(observations),
                stop_reason="no_evidence",
            )

        matching_passages = any(
            isinstance(item.result, list) and bool(item.result)
            for item in successful_searches
        )
        successful_reads = [
            item
            for item in observations
            if item.tool_name == "read_document" and not item.error
        ]
        if not matching_passages:
            return AgentResult(
                answer=(
                    "I could not find relevant passages in the approved local documents. "
                    "Try a different question or add more Markdown or text files."
                ),
                observations=tuple(observations),
                stop_reason="no_evidence",
            )
        if not successful_reads:
            return AgentResult(
                answer=(
                    "A matching passage was found but not read. No answer was generated "
                    "without checking the source text."
                ),
                observations=tuple(observations),
                stop_reason="no_evidence",
            )

        valid_citations = self._validate_citations(action.citations, observations)
        requested_citations: set[tuple[str, int, int]] = set()
        citations_well_formed = True
        for item in action.citations:
            if (
                not isinstance(item, Citation)
                or not isinstance(item.path, str)
                or not item.path
                or len(item.path) > 255
                or not isinstance(item.start_line, int)
                or isinstance(item.start_line, bool)
                or not isinstance(item.end_line, int)
                or isinstance(item.end_line, bool)
            ):
                citations_well_formed = False
                continue
            requested_citations.add((item.path, item.start_line, item.end_line))
        valid_keys = {
            (item.path, item.start_line, item.end_line) for item in valid_citations
        }
        if (
            not citations_well_formed
            or not valid_citations
            or requested_citations != valid_keys
        ):
            return AgentResult(
                answer=(
                    "I withheld the answer because its citations could not be verified "
                    "against the passages read. Please try again."
                ),
                observations=tuple(observations),
                stop_reason="citation_error",
                citations=valid_citations,
            )

        answer = action.text.strip()
        if not answer:
            return AgentResult(
                answer="The planner returned an empty answer. No conclusion was produced.",
                observations=tuple(observations),
                stop_reason="invalid_answer",
                citations=valid_citations,
            )
        return AgentResult(
            answer=answer,
            observations=tuple(observations),
            stop_reason="finished",
            citations=valid_citations,
        )

    def _authorize_tool_call(
        self,
        call: ToolCall,
        observations: Sequence[Observation],
    ) -> Observation | None:
        if call.name not in self._tools.names:
            return None
        if not observations and call.name != "search_documents":
            return Observation(
                tool_name=call.name,
                error="The first research action must search the approved documents.",
            )
        if call.name != "read_document":
            return None

        requested_path = call.arguments.get("path")
        if not isinstance(requested_path, str) or not self._path_was_searched(
            requested_path,
            observations,
        ):
            return Observation(
                tool_name=call.name,
                error="A document must be returned by a prior search before it can be read.",
            )
        return None

    @staticmethod
    def _path_was_searched(path: str, observations: Sequence[Observation]) -> bool:
        for observation in observations:
            if observation.tool_name != "search_documents" or observation.error:
                continue
            if not isinstance(observation.result, list):
                continue
            if any(
                isinstance(item, dict) and item.get("path") == path
                for item in observation.result
            ):
                return True
        return False

    @staticmethod
    def _validate_citations(
        citations: Sequence[Citation],
        observations: Sequence[Observation],
    ) -> tuple[Citation, ...]:
        evidence: list[tuple[str, int, int]] = []
        for observation in observations:
            if observation.tool_name != "read_document" or observation.error:
                continue
            result = observation.result
            if not isinstance(result, dict):
                continue
            path = result.get("path")
            start = result.get("start_line")
            end = result.get("end_line")
            if (
                isinstance(path, str)
                and isinstance(start, int)
                and not isinstance(start, bool)
                and isinstance(end, int)
                and not isinstance(end, bool)
            ):
                evidence.append((path, start, end))

        accepted: list[Citation] = []
        seen: set[tuple[str, int, int]] = set()
        for citation in citations:
            if (
                not isinstance(citation, Citation)
                or not isinstance(citation.path, str)
                or not citation.path
                or len(citation.path) > 255
            ):
                continue
            if (
                not isinstance(citation.start_line, int)
                or isinstance(citation.start_line, bool)
                or not isinstance(citation.end_line, int)
                or isinstance(citation.end_line, bool)
            ):
                continue
            key = (citation.path, citation.start_line, citation.end_line)
            if key in seen:
                continue
            if citation.start_line < 1 or citation.end_line < citation.start_line:
                continue
            if any(
                path == citation.path
                and citation.start_line >= start
                and citation.end_line <= end
                for path, start, end in evidence
            ):
                accepted.append(citation)
                seen.add(key)
            if len(accepted) >= 8:
                break
        return tuple(accepted)

    @classmethod
    def _citations_from_observations(
        cls,
        observations: Sequence[Observation],
    ) -> tuple[Citation, ...]:
        candidates: list[Citation] = []
        for observation in observations:
            if observation.tool_name != "read_document" or observation.error:
                continue
            result = observation.result
            if not isinstance(result, dict):
                continue
            path = result.get("path")
            start = result.get("start_line")
            end = result.get("end_line")
            if (
                isinstance(path, str)
                and isinstance(start, int)
                and not isinstance(start, bool)
                and isinstance(end, int)
                and not isinstance(end, bool)
            ):
                candidates.append(Citation(path, start, end))
        return cls._validate_citations(candidates, observations)
