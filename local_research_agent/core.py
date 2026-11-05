from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeAlias


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, str]


@dataclass(frozen=True)
class FinalAnswer:
    text: str


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


class Planner(Protocol):
    def choose_next_action(
        self,
        goal: str,
        observations: Sequence[Observation],
    ) -> Action: ...


class ToolError(Exception):
    pass


ToolHandler = Callable[[dict[str, str]], object]


class ToolRegistry:
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
    def __init__(
        self,
        planner: Planner,
        tools: ToolRegistry,
        max_steps: int = 4,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self._planner = planner
        self._tools = tools
        self._max_steps = max_steps

    def run(self, goal: str) -> AgentResult:
        if not goal.strip():
            raise ValueError("goal must not be empty")

        observations: list[Observation] = []
        for _ in range(self._max_steps + 1):
            action = self._planner.choose_next_action(goal, tuple(observations))
            if isinstance(action, FinalAnswer):
                return AgentResult(
                    answer=action.text,
                    observations=tuple(observations),
                    stop_reason="finished",
                )

            if len(observations) >= self._max_steps:
                return AgentResult(
                    answer="Stopped: maximum tool steps reached.",
                    observations=tuple(observations),
                    stop_reason="max_steps",
                )

            observations.append(self._tools.execute(action))

        return AgentResult(
            answer="Stopped: maximum tool steps reached.",
            observations=tuple(observations),
            stop_reason="max_steps",
        )
