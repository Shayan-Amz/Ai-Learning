from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from local_research_agent.api import create_app
from local_research_agent.config import Settings

UI_HEADERS = {"X-Requested-With": "LocalResearchAgent"}


def make_client(tmp_path: Path, settings: Settings | None = None) -> TestClient:
    app_settings = settings or Settings(data_dir=tmp_path / "agent-data")
    return TestClient(create_app(app_settings, seed_samples=False))


def test_home_and_health_expose_local_app_without_private_paths(tmp_path: Path):
    client = make_client(tmp_path)

    home = client.get("/")
    script = client.get("/assets/app.js")
    styles = client.get("/assets/styles.css")
    health = client.get("/api/health")

    assert home.status_code == 200
    assert script.status_code == 200
    assert "addAssistantMessage" in script.text
    assert styles.status_code == 200
    assert "Ask your documents" in home.text
    assert home.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'self'" in home.headers["content-security-policy"]
    assert "fonts.googleapis.com" not in home.text
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["document_count"] == 0
    assert body["model_mode"] == "offline"
    assert body["allowed_tools"] == ["search_documents", "read_document"]
    assert str(tmp_path) not in health.text
    assert "api_key" not in health.text


def test_state_changing_requests_require_the_app_header(tmp_path: Path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/documents",
        files=[("files", ("note.md", b"Some text", "text/markdown"))],
    )

    assert response.status_code == 403
    assert "note.md" not in str(list(client.app.state.knowledge_dir.iterdir()))


def test_upload_and_delete_are_explicit_and_confined_to_workspace(tmp_path: Path):
    client = make_client(tmp_path)
    content = b"# Approval\nA human must approve every external payment.\n"

    uploaded = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("approval notes.md", content, "text/markdown"))],
    )
    listed = client.get("/api/documents")

    assert uploaded.status_code == 200
    assert uploaded.json()[0]["name"] == "approval_notes.md"
    assert listed.status_code == 200
    assert [item["path"] for item in listed.json()] == ["approval_notes.md"]

    removed = client.delete("/api/documents/approval_notes.md", headers=UI_HEADERS)
    assert removed.status_code == 200
    assert removed.json() == {"status": "removed", "path": "approval_notes.md"}
    assert client.get("/api/documents").json() == []


def test_upload_rejects_unsupported_encoding_duplicates_and_oversized_files(tmp_path: Path):
    client = make_client(tmp_path)

    unsupported = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("private.csv", b"x,y", "text/csv"))],
    )
    invalid_encoding = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("bad.md", b"\xff\xfe\xfa", "text/markdown"))],
    )
    uploaded = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("same.txt", b"hello world", "text/plain"))],
    )
    duplicate = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("same.txt", b"different", "text/plain"))],
    )
    oversized = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("large.txt", b"x" * (5 * 1024 * 1024 + 1), "text/plain"))],
    )

    assert unsupported.status_code == 415
    assert invalid_encoding.status_code == 415
    assert uploaded.status_code == 200
    assert duplicate.status_code == 409
    assert oversized.status_code == 413
    assert [item["path"] for item in client.get("/api/documents").json()] == ["same.txt"]


def test_upload_sanitizes_windows_and_posix_path_components(tmp_path: Path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("..\\private\\memo.md", b"A safe uploaded note.", "text/markdown"))],
    )

    assert response.status_code == 200
    assert response.json()[0]["path"] == "memo.md"
    assert (client.app.state.knowledge_dir / "memo.md").is_file()
    assert not (tmp_path / "private" / "memo.md").exists()


def test_offline_question_returns_file_line_citations_and_trace(tmp_path: Path):
    client = make_client(tmp_path)
    client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[
            (
                "files",
                (
                    "policy.md",
                    b"# Payment policy\n\nA human must approve every external payment before it is sent.\nKeep a record of the approval.\n",
                    "text/markdown",
                ),
            )
        ],
    )

    response = client.post(
        "/api/ask",
        headers=UI_HEADERS,
        json={"question": "What is the approval rule for payments?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["stop_reason"] == "finished"
    assert body["model_mode"] == "offline"
    assert "human must approve" in body["answer"].casefold()
    assert body["citations"]
    assert body["citations"][0]["file"] == "policy.md"
    assert body["citations"][0]["start_line"] <= body["citations"][0]["end_line"]
    assert "A human must approve" in body["citations"][0]["quote"]
    assert [item["tool"] for item in body["trace"]] == ["search_documents", "read_document"]


def test_offline_question_does_not_invent_an_answer_without_matches(tmp_path: Path):
    client = make_client(tmp_path)
    client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("note.md", b"The garden needs water every morning.", "text/markdown"))],
    )

    response = client.post(
        "/api/ask",
        headers=UI_HEADERS,
        json={"question": "What is the tuition policy?"},
    )

    assert response.status_code == 200
    assert response.json()["citations"] == []
    assert "could not find relevant passages" in response.json()["answer"].casefold()
    assert response.json()["trace"][0]["detail"].startswith("Found 0")


def test_question_validation_and_remote_model_consent(tmp_path: Path):
    remote_settings = Settings(
        data_dir=tmp_path / "remote-data",
        llm_base_url="https://model.example/v1",
        llm_model="test-model",
        llm_api_key="do-not-return-this-secret",
    )
    client = make_client(tmp_path, remote_settings)

    too_short = client.post("/api/ask", headers=UI_HEADERS, json={"question": "ok"})
    consent_required = client.post(
        "/api/ask",
        headers=UI_HEADERS,
        json={"question": "Research my local notes."},
    )
    health = client.get("/api/health").json()

    assert too_short.status_code == 422
    assert consent_required.status_code == 428
    assert health["model_mode"] == "remote"
    assert "do-not-return-this-secret" not in str(health)


def test_remote_question_with_consent_runs_search_read_and_validated_finish(tmp_path: Path, monkeypatch):
    import json as json_module

    import httpx

    from local_research_agent import planner as planner_module

    client = make_client(
        tmp_path,
        Settings(
            data_dir=tmp_path / "remote-data",
            llm_base_url="https://model.example/v1",
            llm_model="test-model",
            llm_api_key="test-key",
        ),
    )
    client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("policy.md", b"Human approval is required before sending a payment.", "text/markdown"))],
    )
    calls: list[dict[str, object]] = []
    actions = [
        ("search_documents", {"query": "human approval"}),
        ("read_document", {"path": "policy.md", "start_line": 1, "end_line": 1}),
        (
            "finish",
            {
                "answer": "Human approval is required before sending a payment [1].",
                "citations": [{"path": "policy.md", "start_line": 1, "end_line": 1}],
            },
        ),
    ]

    def fake_post(url, *, headers, json: dict[str, object], timeout):
        calls.append({"url": url, "headers": headers, "payload": json, "timeout": timeout})
        name, arguments = actions[len(calls) - 1]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": name,
                                        "arguments": json_module.dumps(arguments),
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(planner_module.httpx, "post", fake_post)
    response = client.post(
        "/api/ask",
        headers=UI_HEADERS,
        json={"question": "What requires human approval?", "allow_remote_processing": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["stop_reason"] == "finished"
    assert body["citations"][0]["file"] == "policy.md"
    assert [item["tool"] for item in body["trace"]] == [
        "search_documents",
        "read_document",
    ]
    assert len(calls) == 3
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert "Tool observations" not in calls[0]["payload"]["messages"][-1]["content"]
    assert "Human approval is required" in calls[2]["payload"]["messages"][-1]["content"]
    assert "test-key" not in str(body)
