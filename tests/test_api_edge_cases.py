from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from local_research_agent.api import create_app
from local_research_agent.config import Settings

UI_HEADERS = {"X-Requested-With": "LocalResearchAgent"}


def client_for(data_dir: Path, *, seed_samples: bool = False) -> TestClient:
    return TestClient(create_app(Settings(data_dir=data_dir), seed_samples=seed_samples))


def test_empty_upload_and_duplicate_batch_are_rejected(tmp_path: Path):
    client = client_for(tmp_path / "data")

    empty = client.post("/api/documents", headers=UI_HEADERS, files=[])
    duplicates = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[
            ("files", ("same.txt", b"one", "text/plain")),
            ("files", ("SAME.TXT", b"two", "text/plain")),
        ],
    )

    assert empty.status_code == 400
    assert duplicates.status_code == 409
    assert client.get("/api/documents").json() == []


def test_upload_rejects_hidden_and_empty_documents(tmp_path: Path):
    client = client_for(tmp_path / "data")

    hidden = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", (".secret.md", b"hidden", "text/markdown"))],
    )
    empty = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("empty.md", b"  \n", "text/markdown"))],
    )

    assert hidden.status_code == 400
    assert empty.status_code == 400
    assert client.get("/api/documents").json() == []


def test_upload_limits_number_of_files_per_request(tmp_path: Path):
    client = client_for(tmp_path / "data")
    files = [
        ("files", (f"note-{index}.txt", b"note", "text/plain"))
        for index in range(11)
    ]

    response = client.post("/api/documents", headers=UI_HEADERS, files=files)

    assert response.status_code == 413
    assert client.get("/api/documents").json() == []


def test_upload_limits_total_workspace_documents(tmp_path: Path):
    client = client_for(tmp_path / "data")
    root = client.app.state.knowledge_dir
    for index in range(100):
        (root / f"doc-{index}.md").write_text("short note", encoding="utf-8")

    response = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("extra.md", b"one more", "text/markdown"))],
    )

    assert response.status_code == 413
    assert "100 documents" in response.json()["detail"]


def test_upload_limits_total_workspace_bytes(tmp_path: Path):
    client = client_for(tmp_path / "data")
    oversized_workspace_file = client.app.state.knowledge_dir / "existing.txt"
    with oversized_workspace_file.open("wb") as handle:
        handle.truncate(50 * 1024 * 1024)

    response = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("extra.md", b"small", "text/markdown"))],
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "The knowledge folder is limited to 50 MiB."


def test_failed_multi_file_write_rolls_back_partial_upload(tmp_path: Path, monkeypatch):
    import local_research_agent.api as api_module

    client = client_for(tmp_path / "data")
    real_replace = api_module.os.replace
    calls = 0

    def fail_second_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("private filesystem details")
        real_replace(source, destination)

    monkeypatch.setattr(api_module.os, "replace", fail_second_replace)
    response = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[
            ("files", ("first.txt", b"first", "text/plain")),
            ("files", ("second.txt", b"second", "text/plain")),
        ],
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Could not store the selected documents."
    assert client.get("/api/documents").json() == []
    assert not any(path.name.startswith(".upload-") for path in client.app.state.knowledge_dir.iterdir())


def test_delete_rejects_invalid_unsupported_and_missing_paths(tmp_path: Path):
    client = client_for(tmp_path / "data")
    root = client.app.state.knowledge_dir
    (root / "private.csv").write_text("private", encoding="utf-8")

    traversal = client.delete("/api/documents/%2E%2E%2Fprivate.csv", headers=UI_HEADERS)
    unsupported = client.delete("/api/documents/private.csv", headers=UI_HEADERS)
    missing = client.delete("/api/documents/missing.md", headers=UI_HEADERS)

    assert traversal.status_code in {400, 404}
    assert unsupported.status_code == 404
    assert missing.status_code == 404
    assert (root / "private.csv").is_file()


def test_document_list_handles_invalid_utf8_without_exposing_absolute_paths(tmp_path: Path):
    client = client_for(tmp_path / "data")
    (client.app.state.knowledge_dir / "broken.md").write_bytes(b"\xff")

    response = client.get("/api/documents")

    assert response.status_code == 200
    assert response.json()[0]["path"] == "broken.md"
    assert response.json()[0]["lines"] is None
    assert str(tmp_path) not in response.text


def test_default_workspace_seeds_samples_once_and_does_not_restore_deleted_files(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data")
    first = TestClient(create_app(settings, seed_samples=True))
    sample_paths = {item["path"] for item in first.get("/api/documents").json()}
    assert sample_paths == {"agent-basics.md", "safe-tool-use.md"}

    removed = first.delete("/api/documents/agent-basics.md", headers=UI_HEADERS)
    second = TestClient(create_app(settings, seed_samples=True))

    assert removed.status_code == 200
    assert {item["path"] for item in second.get("/api/documents").json()} == {"safe-tool-use.md"}


def test_windows_reserved_upload_name_is_made_portable(tmp_path: Path):
    client = client_for(tmp_path / "data")

    response = client.post(
        "/api/documents",
        headers=UI_HEADERS,
        files=[("files", ("CON.md", b"not a device file", "text/markdown"))],
    )

    assert response.status_code == 200
    assert response.json()[0]["name"] == "document_CON.md"
