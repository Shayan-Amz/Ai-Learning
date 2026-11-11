from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from local_research_agent.core import (
    Action,
    FinalAnswer,
    Observation,
    PlannerError,
    ResearchAgent,
    ToolCall,
    ToolRegistry,
)
from local_research_agent.tools import build_read_only_tools

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "local_research_agent" / "knowledge"


class FirstActionPlanner:
    def __init__(self, action: Action):
        self.action = action

    def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
        return self.action


def test_agent_refuses_to_finish_without_searching_documents():
    agent = ResearchAgent(FirstActionPlanner(FinalAnswer("Unverified answer")), ToolRegistry({}))

    result = agent.run("What is in my notes?")

    assert result.stop_reason == "no_evidence"
    assert "no research answer" in result.answer.casefold()


def test_agent_requires_search_as_the_first_tool_action():
    class ReadFirst:
        def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
            if not observations:
                return ToolCall("read_document", {"path": "safe-tool-use.md"})
            return FinalAnswer("The planner tried to skip search.")

    agent = ResearchAgent(ReadFirst(), build_read_only_tools(KNOWLEDGE_DIR))
    result = agent.run("Read a note directly")

    assert result.stop_reason == "no_evidence"
    assert result.observations[0].error == "The first research action must search the approved documents."


def test_agent_requires_read_path_to_come_from_a_prior_search():
    calls: list[str] = []

    def search(arguments: dict[str, object]) -> list[dict[str, object]]:
        return [{"path": "approved.md", "start_line": 1, "end_line": 1}]

    def read(arguments: dict[str, object]) -> dict[str, object]:
        calls.append(str(arguments.get("path")))
        return {"path": "approved.md", "start_line": 1, "end_line": 1, "content": "1: evidence"}

    tools = ToolRegistry({"search_documents": search, "read_document": read})

    class Guesser:
        def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
            if not observations:
                return ToolCall("search_documents", {"query": goal})
            if len(observations) == 1:
                return ToolCall("read_document", {"path": "guessed-private.md"})
            return FinalAnswer("I found evidence.")

    result = ResearchAgent(Guesser(), tools, max_steps=3).run("search")

    assert calls == []
    assert result.stop_reason == "no_evidence"
    assert result.observations[1].error == (
        "A document must be returned by a prior search before it can be read."
    )


def test_agent_withholds_answer_when_search_hit_was_not_read():
    class SearchThenFinish:
        def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
            if not observations:
                return ToolCall("search_documents", {"query": "human approval"})
            return FinalAnswer("Unsupported synthesis")

    result = ResearchAgent(
        SearchThenFinish(),
        build_read_only_tools(KNOWLEDGE_DIR),
    ).run("Find human approval")

    assert result.stop_reason == "no_evidence"
    assert "was found but not read" in result.answer


def test_agent_requires_valid_citations_after_reading_evidence():
    class ReadThenUncited:
        def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
            if not observations:
                return ToolCall("search_documents", {"query": "human approval"})
            if len(observations) == 1:
                hit = observations[0].result[0]
                return ToolCall(
                    "read_document",
                    {
                        "path": hit["path"],
                        "start_line": hit["start_line"],
                        "end_line": hit["end_line"],
                    },
                )
            return FinalAnswer("This response has no verifiable reference.")

    result = ResearchAgent(ReadThenUncited(), build_read_only_tools(KNOWLEDGE_DIR)).run(
        "Find human approval"
    )

    assert result.stop_reason == "citation_error"
    assert result.citations == ()
    assert "withheld" in result.answer


def test_agent_rejects_an_invalid_planner_action():
    result = ResearchAgent(FirstActionPlanner("not-an-action"), ToolRegistry({})).run("Research")

    assert result.stop_reason == "invalid_action"
    assert "invalid action" in result.answer.casefold()


def test_agent_gives_actionable_safe_message_when_local_model_is_unreachable():
    class UnreachableModel:
        def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
            raise PlannerError("The configured model could not be reached.")

    result = ResearchAgent(UnreachableModel(), ToolRegistry({})).run("Research")

    assert result.stop_reason == "planner_error"
    assert "make sure it is running" in result.answer
    assert ".env" in result.answer


def test_agent_stops_cleanly_on_a_planner_failure():
    class BrokenPlanner:
        def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
            raise PlannerError("do not expose provider internals")

    result = ResearchAgent(BrokenPlanner(), ToolRegistry({})).run("Research")

    assert result.stop_reason == "planner_error"
    assert "provider internals" not in result.answer
