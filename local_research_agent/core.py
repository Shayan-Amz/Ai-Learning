from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeAlias

_GROUNDING_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "being",
        "but",
        "by",
        "do",
        "does",
        "did",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "hers",
        "him",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "me",
        "my",
        "of",
        "on",
        "or",
        "our",
        "ours",
        "she",
        "so",
        "than",
        "that",
        "the",
        "their",
        "them",
        "there",
        "these",
        "they",
        "this",
        "those",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
        "yours",
        "according",
        "answer",
        "based",
        "document",
        "documents",
        "evidence",
        "found",
        "information",
        "local",
        "note",
        "notes",
        "passage",
        "passages",
        "provided",
        "relevant",
        "result",
        "results",
        "retrieved",
        "source",
        "sources",
        "stated",
        "states",
        "say",
        "says",
        "said",
        "show",
        "shows",
        "mention",
        "mentions",
        "describe",
        "describes",
        "indicate",
        "indicates",
        "report",
        "reports",
        "line",
        "lines",
        "citation",
        "citations",
        "require",
        "requires",
        "required",
        "requirement",
        "requirements",
        "need",
        "needs",
        "necessary",
        "necessity",
        "must",
        "first",
        "happen",
        "happens",
        "occur",
        "occurs",
    }
)
_GENERIC_SOURCE_PREFIX = re.compile(
    r"^\s*(?:(?:according to|based on|in|from)\s+(?:the\s+)?(?:provided\s+)?"
    r"(?:document|notes?|source|passage|evidence)|(?:the\s+)?"
    r"(?:document|notes?|source|passage|evidence)\s+"
    r"(?:says?|states?|mentions?|notes?|indicates?|shows?|describes?|reports?))"
    r"\s*[:,]?\s*(?:that\s+)?",
    re.IGNORECASE,
)


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


def _safe_planner_error_message(error: PlannerError) -> str:
    """Translate known planner failures into actionable text without exposing internals."""
    message = str(error)
    if message == "The configured model could not be reached.":
        return (
            "Could not reach the configured model. If using Ollama, make sure it is running "
            "and that .env points to its local OpenAI-compatible /v1 endpoint."
        )
    if message == "The configured model timed out.":
        return (
            "The configured model timed out. Try a smaller local model or increase "
            "LOCAL_RESEARCH_LLM_TIMEOUT_SECONDS in .env."
        )
    if message.startswith("The configured model returned HTTP "):
        status_code = message.rsplit(" ", 1)[-1].rstrip(".")
        if status_code.isdigit():
            if status_code == "404":
                return (
                    "The model endpoint or model name was not found (HTTP 404). Check .env; "
                    "for Ollama, make sure you have pulled the configured model."
                )
            if status_code in {"400", "422"}:
                return (
                    f"The model rejected the request (HTTP {status_code}). Check that the "
                    "selected model supports tool calling."
                )
            return f"The configured model returned HTTP {status_code}. Check its URL and model settings."
    return (
        "The planner could not complete this request. Check the configured model and try again. "
        "Provider internals were not included."
    )


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
        grounding_retry_used = False
        grounding_retry_read_attempted = False
        for _ in range(self._max_steps + 2):
            try:
                action = self._planner.choose_next_action(goal, tuple(observations))
            except PlannerError as error:
                return AgentResult(
                    answer=_safe_planner_error_message(error),
                    observations=tuple(observations),
                    stop_reason="planner_error",
                    citations=self._fallback_citations(observations),
                )

            if isinstance(action, FinalAnswer):
                if (
                    grounding_retry_used
                    and not grounding_retry_read_attempted
                    and not self._has_new_read_after_grounding_feedback(observations)
                    and len(observations) < self._max_steps
                ):
                    additional_read = self._next_unread_search_result(observations)
                    if additional_read is not None:
                        grounding_retry_read_attempted = True
                        authorization_error = self._authorize_tool_call(
                            additional_read,
                            observations,
                        )
                        observations.append(
                            authorization_error
                            if authorization_error
                            else self._tools.execute(additional_read)
                        )
                        continue

                result = self._finish(action, observations)
                if (
                    result.stop_reason == "ungrounded_answer"
                    and not grounding_retry_used
                    and len(observations) + 2 < self._max_steps
                ):
                    observations.append(
                        Observation(
                            tool_name="answer_validation",
                            result=(
                                "The previous answer did not match its cited text. Search for or "
                                "read another passage; do not repeat unsupported claims."
                            ),
                        )
                    )
                    grounding_retry_used = True
                    continue
                return result

            if not isinstance(action, ToolCall):
                return AgentResult(
                    answer="The planner returned an invalid action. No further action was taken.",
                    observations=tuple(observations),
                    stop_reason="invalid_action",
                    citations=self._fallback_citations(observations),
                )

            if len(observations) >= self._max_steps:
                return AgentResult(
                    answer="Stopped safely: the maximum number of tool steps was reached.",
                    observations=tuple(observations),
                    stop_reason="max_steps",
                    citations=self._fallback_citations(observations),
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
            citations=self._fallback_citations(observations),
        )

    def _finish(
        self,
        action: FinalAnswer,
        observations: Sequence[Observation],
    ) -> AgentResult:
        successful_searches = [
            item for item in observations if item.tool_name == "search_documents" and not item.error
        ]
        if not successful_searches:
            return AgentResult(
                answer="No approved local document was searched, so no research answer was produced.",
                observations=tuple(observations),
                stop_reason="no_evidence",
            )

        matching_passages = any(
            isinstance(item.result, list) and bool(item.result) for item in successful_searches
        )
        successful_reads = [
            item for item in observations if item.tool_name == "read_document" and not item.error
        ]
        if not matching_passages:
            return AgentResult(
                answer=(
                    "No matching passages were found. Offline mode searches for overlapping words in your files; "
                    "it does not understand synonyms or generate summaries. Try an exact term from "
                    "the document, or configure a local model for natural-language answers."
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
        valid_keys = {(item.path, item.start_line, item.end_line) for item in valid_citations}
        if not citations_well_formed or not valid_citations or requested_citations != valid_keys:
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

        grounded_answer = self._ground_answer(answer, valid_citations, observations)
        if grounded_answer is None:
            return AgentResult(
                answer=(
                    "I withheld the answer because one or more factual claims could not be "
                    "matched to the cited source text. Please try a question about a point "
                    "stated directly in the document."
                ),
                observations=tuple(observations),
                stop_reason="ungrounded_answer",
            )
        grounded_text, grounded_citations = grounded_answer
        return AgentResult(
            answer=grounded_text,
            observations=tuple(observations),
            stop_reason="finished",
            citations=grounded_citations,
        )

    @staticmethod
    def _successful_read_ranges(
        observations: Sequence[Observation],
    ) -> list[tuple[str, int, int]]:
        ranges: list[tuple[str, int, int]] = []
        for observation in observations:
            if observation.tool_name != "read_document" or observation.error:
                continue
            result = observation.result
            if not isinstance(result, dict):
                continue
            path = result.get("path")
            start = result.get("start_line")
            end = result.get("end_line")
            content = result.get("content")
            if (
                isinstance(path, str)
                and isinstance(start, int)
                and not isinstance(start, bool)
                and isinstance(end, int)
                and not isinstance(end, bool)
                and start >= 1
                and end >= start
                and end - start + 1 <= 40
                and isinstance(content, str)
                and content.strip()
            ):
                ranges.append((path, start, end))
        return ranges

    @staticmethod
    def _search_result_ranges(
        observations: Sequence[Observation],
    ) -> list[tuple[str, int, int]]:
        ranges: list[tuple[str, int, int]] = []
        for observation in observations:
            if (
                observation.tool_name != "search_documents"
                or observation.error
                or not isinstance(observation.result, list)
            ):
                continue
            for result in observation.result:
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
                    and start >= 1
                    and end >= start
                    and end - start + 1 <= 40
                ):
                    ranges.append((path, start, end))
        return ranges

    @staticmethod
    def _first_unread_range(
        path: str,
        start: int,
        end: int,
        read_ranges: Sequence[tuple[str, int, int]],
    ) -> tuple[int, int] | None:
        cursor = start
        matching_ranges = sorted(
            (read_start, read_end)
            for read_path, read_start, read_end in read_ranges
            if read_path == path and read_start <= end and read_end >= start
        )
        for read_start, read_end in matching_ranges:
            if read_start > cursor:
                return cursor, min(end, read_start - 1)
            cursor = max(cursor, read_end + 1)
            if cursor > end:
                return None
        return (cursor, end) if cursor <= end else None

    @classmethod
    def _has_new_read_after_grounding_feedback(
        cls,
        observations: Sequence[Observation],
    ) -> bool:
        feedback_index = next(
            (
                index
                for index in range(len(observations) - 1, -1, -1)
                if observations[index].tool_name == "answer_validation"
            ),
            None,
        )
        if feedback_index is None:
            return False

        retry_observations = observations[feedback_index + 1 :]
        earlier_reads = cls._successful_read_ranges(observations[:feedback_index])
        search_ranges = cls._search_result_ranges(retry_observations)
        later_reads = cls._successful_read_ranges(retry_observations)
        for read_path, read_start, read_end in later_reads:
            for search_path, search_start, search_end in search_ranges:
                overlap_start = max(read_start, search_start)
                overlap_end = min(read_end, search_end)
                if (
                    read_path == search_path
                    and overlap_start <= overlap_end
                    and cls._first_unread_range(
                        read_path,
                        overlap_start,
                        overlap_end,
                        earlier_reads,
                    )
                    is not None
                ):
                    return True
        return False

    @classmethod
    def _next_unread_search_result(
        cls,
        observations: Sequence[Observation],
    ) -> ToolCall | None:
        feedback_index = next(
            (
                index
                for index in range(len(observations) - 1, -1, -1)
                if observations[index].tool_name == "answer_validation"
            ),
            None,
        )
        if feedback_index is None:
            return None

        read_ranges = cls._successful_read_ranges(observations)
        partially_unread_candidate: ToolCall | None = None
        for observation in reversed(observations[feedback_index + 1 :]):
            if (
                observation.tool_name != "search_documents"
                or observation.error
                or not isinstance(observation.result, list)
            ):
                continue
            for result in observation.result:
                if not isinstance(result, dict):
                    continue
                path = result.get("path")
                start = result.get("start_line")
                end = result.get("end_line")
                if (
                    not isinstance(path, str)
                    or not isinstance(start, int)
                    or isinstance(start, bool)
                    or not isinstance(end, int)
                    or isinstance(end, bool)
                    or start < 1
                    or end < start
                    or end - start + 1 > 40
                ):
                    continue
                unread_range = cls._first_unread_range(path, start, end, read_ranges)
                if unread_range is None:
                    continue
                candidate = ToolCall(
                    "read_document",
                    {"path": path, "start_line": start, "end_line": end},
                )
                if unread_range == (start, end):
                    return candidate
                if partially_unread_candidate is None:
                    partially_unread_candidate = candidate
        return partially_unread_candidate

    @classmethod
    def _ground_answer(
        cls,
        answer: str,
        citations: Sequence[Citation],
        observations: Sequence[Observation],
    ) -> tuple[str, tuple[Citation, ...]] | None:
        """Keep an answer only when each sentence matches its cited source text."""
        evidence_by_citation = [
            cls._citation_evidence_lines(citation, observations) for citation in citations
        ]
        if not evidence_by_citation or not any(evidence_by_citation):
            return None

        source_footer = re.search(r"(?im)^\s*Sources:.*$", answer)
        if source_footer:
            answer = answer[: source_footer.start()].rstrip()
        answer_body = answer
        sentences = re.split(
            r"\n+|(?<=[!?;])\s+|(?<!\d)\.\s+",
            answer_body,
        )
        used_citations: set[int] = set()
        checked_claim = False
        for sentence in sentences:
            references = [int(value) - 1 for value in re.findall(r"\[(\d+)\]", sentence)]
            claim = re.sub(r"\[(\d+)\]", "", sentence)
            claim = re.sub(r"^\s*(?:[-*•]\s*|#{1,6}\s*|\d+[.)]\s*)", "", claim)
            claim = _GENERIC_SOURCE_PREFIX.sub("", claim, count=1).strip()
            claim_tokens = cls._grounding_tokens(claim)
            if not claim_tokens:
                continue
            checked_claim = True

            if references:
                referenced = set(references)
                if any(index < 0 or index >= len(evidence_by_citation) for index in referenced):
                    return None
                for index in referenced:
                    if not cls._claim_matches_lines(claim_tokens, evidence_by_citation[index]):
                        return None
                    used_citations.add(index)
                continue

            matching = [
                index
                for index, lines in enumerate(evidence_by_citation)
                if cls._claim_matches_lines(claim_tokens, lines)
            ]
            if not matching:
                return None
            used_citations.update(matching)

        if not checked_claim or not used_citations:
            return None

        selected_indexes = sorted(used_citations)
        citation_numbers = {
            original_index + 1: selected_index + 1
            for selected_index, original_index in enumerate(selected_indexes)
        }

        def remap_reference(match: re.Match[str]) -> str:
            new_number = citation_numbers.get(int(match.group(1)))
            return f"[{new_number}]" if new_number is not None else ""

        grounded_answer = re.sub(r"\[(\d+)\]", remap_reference, answer)
        grounded_citations = tuple(citations[index] for index in selected_indexes)
        return grounded_answer, grounded_citations

    @staticmethod
    def _citation_evidence_lines(
        citation: Citation,
        observations: Sequence[Observation],
    ) -> tuple[str, ...]:
        evidence: list[str] = []
        for observation in observations:
            if observation.tool_name != "read_document" or observation.error:
                continue
            result = observation.result
            if not isinstance(result, dict) or result.get("path") != citation.path:
                continue
            start = result.get("start_line")
            end = result.get("end_line")
            content = result.get("content")
            if (
                not isinstance(start, int)
                or isinstance(start, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
                or not isinstance(content, str)
                or citation.start_line < start
                or citation.end_line > end
            ):
                continue

            numbered_lines: list[str] = []
            has_line_numbers = False
            for line in content.splitlines():
                match = re.match(r"^\s*(\d+):\s?(.*)$", line)
                if not match:
                    continue
                has_line_numbers = True
                line_number = int(match.group(1))
                if citation.start_line <= line_number <= citation.end_line:
                    numbered_lines.append(match.group(2).strip())
            if has_line_numbers:
                evidence.extend(numbered_lines)
            elif citation.start_line == start and citation.end_line == end:
                evidence.extend(line.strip() for line in content.splitlines())
        return tuple(evidence)

    @staticmethod
    def _grounding_tokens(text: str) -> tuple[str, ...]:
        tokens: list[str] = []
        for token in re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE):
            if token in _GROUNDING_STOP_WORDS:
                continue
            if token.endswith("ization") and len(token) > 9:
                token = token[:-5]
            elif token.endswith("ies") and len(token) > 5:
                token = token[:-3] + "y"
            elif token.endswith("ing") and len(token) > 6:
                token = token[:-3]
                if len(token) > 2 and token[-1] == token[-2] and token[-1] not in "aeiou":
                    token = token[:-1]
            elif token.endswith("ed") and len(token) > 5:
                token = token[:-2]
                if len(token) > 2 and token[-1] == token[-2] and token[-1] not in "aeiou":
                    token = token[:-1]
            elif token.endswith("s") and len(token) > 4:
                token = token[:-1]
            if token.endswith("al") and len(token) > 6:
                token = token[:-2]
            if token.endswith("e") and len(token) > 5:
                token = token[:-1]
            if token not in _GROUNDING_STOP_WORDS:
                tokens.append(token)
        return tuple(tokens)

    @classmethod
    def _claim_matches_lines(
        cls,
        claim_tokens: Sequence[str],
        evidence_lines: Sequence[str],
    ) -> bool:
        for line in evidence_lines:
            evidence_tokens = cls._grounding_tokens(line)
            if not evidence_tokens or not set(claim_tokens).issubset(evidence_tokens):
                continue
            if len(claim_tokens) == 1:
                return True
            if any(
                claim_tokens[index : index + 2]
                == evidence_tokens[evidence_index : evidence_index + 2]
                for index in range(len(claim_tokens) - 1)
                for evidence_index in range(len(evidence_tokens) - 1)
            ):
                return True
        return False

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
                isinstance(item, dict) and item.get("path") == path for item in observation.result
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
                path == citation.path and citation.start_line >= start and citation.end_line <= end
                for path, start, end in evidence
            ):
                accepted.append(citation)
                seen.add(key)
            if len(accepted) >= 8:
                break
        return tuple(accepted)

    @classmethod
    def _fallback_citations(
        cls,
        observations: Sequence[Observation],
    ) -> tuple[Citation, ...]:
        if any(item.tool_name == "answer_validation" for item in observations):
            return ()
        return cls._citations_from_observations(observations)

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
