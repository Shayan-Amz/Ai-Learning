from __future__ import annotations

import json
from collections.abc import Sequence

import httpx
import pytest

from local_research_agent.core import (
    Citation,
    FinalAnswer,
    Observation,
    PlannerError,
    ToolCall,
)
from local_research_agent.planner import OpenAICompatiblePlanner


def test_openai_compatible_planner_turns_function_call_into_tool_action(monkeypatch):
    captured: dict[str, object] = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "payload": json, "timeout": timeout})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "search_documents",
                                        "arguments": '{"query":"approval"}',
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("local_research_agent.planner.httpx.post", fake_post)
    planner = OpenAICompatiblePlanner(
        "http://127.0.0.1:11434/v1/",
        "local-tool-model",
        timeout_seconds=8,
    )

    action = planner.choose_next_action("Find the approval note.", ())

    assert action == ToolCall("search_documents", {"query": "approval"})
    assert captured["url"] == "http://127.0.0.1:11434/v1/chat/completions"
    assert captured["timeout"] == 8
    assert captured["payload"]["tools"]
    assert captured["payload"]["messages"][0]["role"] == "system"


def test_openai_compatible_planner_builds_finish_with_structured_citations(monkeypatch):
    response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "finish",
                                    "arguments": json.dumps(
                                        {
                                            "answer": "A human must approve this action [1].",
                                            "citations": [
                                                {
                                                    "path": "policy.md",
                                                    "start_line": 5,
                                                    "end_line": 7,
                                                }
                                            ],
                                        }
                                    ),
                                }
                            }
                        ]
                    }
                }
            ]
        },
    )
    monkeypatch.setattr("local_research_agent.planner.httpx.post", lambda *args, **kwargs: response)
    planner = OpenAICompatiblePlanner("https://model.example/v1", "test-model", "secret")

    action = planner.choose_next_action(
        "What requires approval?",
        [Observation("read_document", {"path": "policy.md", "start_line": 5, "end_line": 7})],
    )

    assert action == FinalAnswer(
        "A human must approve this action [1].",
        (Citation("policy.md", 5, 7),),
    )


def test_openai_compatible_planner_converts_network_errors_to_safe_planner_errors(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("internal transport details")

    monkeypatch.setattr("local_research_agent.planner.httpx.post", fail)
    planner = OpenAICompatiblePlanner("https://model.example/v1", "test-model")

    with pytest.raises(PlannerError, match="could not be reached") as error:
        planner.choose_next_action("Search my notes", ())
    assert "internal transport details" not in str(error.value)


def test_unknown_model_tool_call_is_not_executable_by_the_agent():
    action = OpenAICompatiblePlanner._to_action("run_shell", {"command": "whoami"})

    assert action == ToolCall("run_shell", {"command": "whoami"})


def test_model_text_without_tool_call_carries_only_observed_citations(monkeypatch):
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "This statement is based on the passage [1]."}}]},
    )
    monkeypatch.setattr("local_research_agent.planner.httpx.post", lambda *args, **kwargs: response)
    planner = OpenAICompatiblePlanner("https://model.example/v1", "test-model")
    observations: Sequence[Observation] = [
        Observation("read_document", {"path": "note.md", "start_line": 2, "end_line": 4})
    ]

    action = planner.choose_next_action("Summarize", observations)

    assert action == FinalAnswer(
        "This statement is based on the passage [1].",
        (Citation("note.md", 2, 4),),
    )
