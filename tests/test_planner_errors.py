from __future__ import annotations

import httpx
import pytest

from local_research_agent.core import PlannerError
from local_research_agent.planner import OpenAICompatiblePlanner


def make_planner():
    return OpenAICompatiblePlanner("https://model.example/v1", "test-model")


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(429, json={"error": "private provider body"}), "HTTP 429"),
        (httpx.Response(200, json={"choices": []}), "invalid response"),
        (
            httpx.Response(200, json={"choices": [{"message": {"tool_calls": [{"function": {"name": "search_documents", "arguments": "{"}}]}}]}),
            "invalid tool call",
        ),
        (httpx.Response(200, json={"choices": [{"message": {}}]}), "neither an action nor an answer"),
    ],
)
def test_planner_reports_provider_response_failures_safely(monkeypatch, response, message):
    monkeypatch.setattr("local_research_agent.planner.httpx.post", lambda *args, **kwargs: response)

    with pytest.raises(PlannerError, match=message) as error:
        make_planner().choose_next_action("Find a note", ())
    assert "private provider body" not in str(error.value)


def test_planner_rejects_multiple_actions_in_one_model_response(monkeypatch):
    response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {"function": {"name": "search_documents", "arguments": '{"query":"a"}'}},
                            {"function": {"name": "search_documents", "arguments": '{"query":"b"}'}},
                        ]
                    }
                }
            ]
        },
    )
    monkeypatch.setattr("local_research_agent.planner.httpx.post", lambda *args, **kwargs: response)

    with pytest.raises(PlannerError, match="multiple actions"):
        make_planner().choose_next_action("Find a note", ())


def test_planner_reports_timeout_without_transport_details(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("sensitive request body")

    monkeypatch.setattr("local_research_agent.planner.httpx.post", timeout)

    with pytest.raises(PlannerError, match="timed out") as error:
        make_planner().choose_next_action("Find a note", ())
    assert "sensitive request body" not in str(error.value)


def test_planner_rejects_invalid_finish_schema(monkeypatch):
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
                                    "arguments": '{"answer":"invalid","citations":"not-a-list"}',
                                }
                            }
                        ]
                    }
                }
            ]
        },
    )
    monkeypatch.setattr("local_research_agent.planner.httpx.post", lambda *args, **kwargs: response)

    with pytest.raises(PlannerError, match="invalid citations"):
        make_planner().choose_next_action("Find a note", ())


def test_planner_ignores_malformed_citation_items_but_returns_valid_ones():
    from local_research_agent.core import Citation, FinalAnswer

    action = OpenAICompatiblePlanner._to_action(
        "finish",
        {
            "answer": "Supported by evidence [1].",
            "citations": [
                "not an object",
                {"path": "note.md", "start_line": True, "end_line": 1},
                {"path": "note.md", "start_line": 2, "end_line": 3},
            ],
        },
    )

    assert action == FinalAnswer(
        "Supported by evidence [1].",
        (Citation("note.md", 2, 3),),
    )
