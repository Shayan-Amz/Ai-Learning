from collections.abc import Sequence
from pathlib import Path

import pytest

from local_research_agent.core import (
    Action,
    Observation,
    ResearchAgent,
    ToolCall,
)
from local_research_agent.planner import DemoPlanner
from local_research_agent.tools import build_read_only_tools


KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "local_research_agent" / "knowledge"


def test_demo_agent_searches_reads_and_cites_a_local_source():
    tools = build_read_only_tools(KNOWLEDGE_DIR)
    agent = ResearchAgent(DemoPlanner(), tools, max_steps=3)

    result = agent.run("Find a local note about human approval.")

    assert result.stop_reason == "finished"
    assert [item.tool_name for item in result.observations] == [
        "search_documents",
        "read_document",
    ]
    assert "safe-tool-use.md" in result.answer
    assert "human approval" in result.answer


def test_search_is_case_insensitive_and_returns_line_citations():
    tools = build_read_only_tools(KNOWLEDGE_DIR)
    observation = tools.execute(
        ToolCall("search_documents", {"query": "HUMAN APPROVAL"})
    )

    assert observation.error is None
    assert isinstance(observation.result, list)
    assert observation.result[0]["path"] == "safe-tool-use.md"
    assert isinstance(observation.result[0]["line"], int)


def test_read_tool_rejects_paths_outside_the_approved_folder(tmp_path: Path):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "allowed.md").write_text("Safe note.", encoding="utf-8")
    (tmp_path / "private.md").write_text("Private note.", encoding="utf-8")
    tools = build_read_only_tools(knowledge_dir)

    observation = tools.execute(
        ToolCall("read_document", {"path": "../private.md"})
    )

    assert observation.error == "Document path escapes the knowledge directory."


def test_registry_refuses_unregistered_tools():
    tools = build_read_only_tools(KNOWLEDGE_DIR)
    observation = tools.execute(ToolCall("run_shell", {}))

    assert observation.error == "Tool is not registered."
    assert tools.names == frozenset({"search_documents", "read_document"})


def test_agent_stops_when_the_tool_step_limit_is_reached():
    class RepeatingPlanner:
        def choose_next_action(
            self,
            goal: str,
            observations: Sequence[Observation],
        ) -> Action:
            return ToolCall("search_documents", {"query": "agent"})

    agent = ResearchAgent(
        RepeatingPlanner(),
        build_read_only_tools(KNOWLEDGE_DIR),
        max_steps=1,
    )
    result = agent.run("Search the local notes.")

    assert result.stop_reason == "max_steps"
    assert len(result.observations) == 1
    assert result.answer == "Stopped: maximum tool steps reached."


def test_agent_rejects_an_empty_goal():
    agent = ResearchAgent(DemoPlanner(), build_read_only_tools(KNOWLEDGE_DIR))

    with pytest.raises(ValueError, match="goal must not be empty"):
        agent.run("   ")
