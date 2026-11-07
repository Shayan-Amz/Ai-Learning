from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from local_research_agent.core import (
    Action,
    Citation,
    FinalAnswer,
    Observation,
    ResearchAgent,
    ToolCall,
)
from local_research_agent.planner import DemoPlanner, ExtractivePlanner
from local_research_agent.tools import build_read_only_tools

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "local_research_agent" / "knowledge"


def test_offline_agent_searches_reads_and_returns_verified_citations():
    tools = build_read_only_tools(KNOWLEDGE_DIR)
    agent = ResearchAgent(ExtractivePlanner(), tools, max_steps=6)

    result = agent.run("What should have human approval before an irreversible action?")

    assert result.stop_reason == "finished"
    assert [item.tool_name for item in result.observations] == [
        "search_documents",
        "read_document",
        "read_document",
    ]
    assert "human approval" in result.answer.casefold()
    assert result.citations
    read_results = [
        item.result for item in result.observations if item.tool_name == "read_document"
    ]
    assert all(
        any(
            citation.path == source["path"]
            and citation.start_line >= source["start_line"]
            and citation.end_line <= source["end_line"]
            for source in read_results
        )
        for citation in result.citations
    )


def test_search_is_case_insensitive_ranked_and_returns_line_ranges():
    tools = build_read_only_tools(KNOWLEDGE_DIR)
    observation = tools.execute(
        ToolCall("search_documents", {"query": "HUMAN APPROVAL"})
    )

    assert observation.error is None
    assert isinstance(observation.result, list)
    assert observation.result[0]["path"] == "safe-tool-use.md"
    assert observation.result[0]["start_line"] <= observation.result[0]["end_line"]
    assert "human" in str(observation.result[0]["snippet"]).casefold()


def test_search_returns_no_match_for_unrelated_query():
    tools = build_read_only_tools(KNOWLEDGE_DIR)
    observation = tools.execute(
        ToolCall("search_documents", {"query": "volcanic eruption astronomy"})
    )
    assert observation.error is None
    assert observation.result == []


def test_read_tool_rejects_paths_outside_the_approved_folder(tmp_path: Path):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "allowed.md").write_text("Safe note.", encoding="utf-8")
    (tmp_path / "private.md").write_text("Private note.", encoding="utf-8")
    tools = build_read_only_tools(knowledge_dir)

    observation = tools.execute(ToolCall("read_document", {"path": "../private.md"}))

    assert observation.error == "Document path escapes the approved folder."


def test_read_tool_rejects_unsupported_extension_and_bad_line_range(tmp_path: Path):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "note.md").write_text("First line.\nSecond line.\n", encoding="utf-8")
    (knowledge_dir / "secret.csv").write_text("not a supported document", encoding="utf-8")
    tools = build_read_only_tools(knowledge_dir)

    unsupported = tools.execute(ToolCall("read_document", {"path": "secret.csv"}))
    bad_range = tools.execute(
        ToolCall("read_document", {"path": "note.md", "start_line": 2, "end_line": 8})
    )

    assert unsupported.error == "Only Markdown and plain-text documents can be read."
    assert bad_range.error == "Requested line range is outside the document."


def test_search_rejects_hidden_files_and_symlinks_escaping_root(tmp_path: Path):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "visible.md").write_text("human approval", encoding="utf-8")
    (knowledge_dir / ".hidden.md").write_text("human approval", encoding="utf-8")
    private_file = tmp_path / "private.md"
    private_file.write_text("human approval", encoding="utf-8")
    try:
        (knowledge_dir / "linked.md").symlink_to(private_file)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks are not available in this environment")
    tools = build_read_only_tools(knowledge_dir)

    observation = tools.execute(ToolCall("search_documents", {"query": "human approval"}))

    assert observation.error is None
    assert [item["path"] for item in observation.result] == ["visible.md"]


def test_registry_refuses_unregistered_tools():
    tools = build_read_only_tools(KNOWLEDGE_DIR)
    observation = tools.execute(ToolCall("run_shell", {}))

    assert observation.error == "Tool is not registered."
    assert tools.names == frozenset({"search_documents", "read_document"})


def test_agent_stops_when_tool_step_limit_is_reached():
    class RepeatingPlanner:
        def choose_next_action(
            self,
            goal: str,
            observations: Sequence[Observation],
        ) -> Action:
            return ToolCall("search_documents", {"query": "agent"})

    agent = ResearchAgent(RepeatingPlanner(), build_read_only_tools(KNOWLEDGE_DIR), max_steps=1)
    result = agent.run("Search the local notes.")

    assert result.stop_reason == "max_steps"
    assert len(result.observations) == 1
    assert result.answer.startswith("Stopped safely")


def test_agent_rejects_an_empty_or_overlong_goal():
    agent = ResearchAgent(DemoPlanner(), build_read_only_tools(KNOWLEDGE_DIR))

    with pytest.raises(ValueError, match="goal must not be empty"):
        agent.run("   ")
    with pytest.raises(ValueError, match="1000 characters"):
        agent.run("x" * 1001)


def test_agent_drops_citations_not_present_in_read_observations():
    class CitationPlanner:
        def choose_next_action(
            self,
            goal: str,
            observations: Sequence[Observation],
        ) -> Action:
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
            source = observations[1].result
            return FinalAnswer(
                "An answer with one invented citation.",
                (
                    Citation(source["path"], source["start_line"], source["end_line"]),
                    Citation("private.md", 1, 2),
                ),
            )

    result = ResearchAgent(CitationPlanner(), build_read_only_tools(KNOWLEDGE_DIR)).run("Read the note")

    assert result.stop_reason == "citation_error"
    assert "withheld" in result.answer
    assert len(result.citations) == 1


def test_extractive_planner_answers_with_no_findings_when_search_is_empty():
    planner = ExtractivePlanner()
    action = planner.choose_next_action(
        "Find something unrelated",
        [Observation(tool_name="search_documents", result=[])],
    )

    assert isinstance(action, FinalAnswer)
    assert "could not find" in action.text.casefold()


def test_agent_rejects_invalid_max_steps():
    with pytest.raises(ValueError, match="between 1 and 20"):
        ResearchAgent(DemoPlanner(), build_read_only_tools(KNOWLEDGE_DIR), max_steps=0)
