from __future__ import annotations

from pathlib import Path

import pytest

from local_research_agent.core import ToolCall
from local_research_agent.tools import (
    MAX_FILE_BYTES,
    MAX_READ_LINES,
    build_read_only_tools,
)


def make_tools(tmp_path: Path):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    return knowledge, build_read_only_tools(knowledge)


def test_search_rejects_missing_and_overlong_queries(tmp_path: Path):
    _, tools = make_tools(tmp_path)

    missing = tools.execute(ToolCall("search_documents", {}))
    too_long = tools.execute(ToolCall("search_documents", {"query": "x" * 1001}))

    assert missing.error == "Missing or invalid required argument: query"
    assert too_long.error == "Search query is too long."


def test_search_returns_empty_for_blank_or_stopword_only_queries(tmp_path: Path):
    knowledge, tools = make_tools(tmp_path)
    (knowledge / "note.md").write_text("A simple local note.", encoding="utf-8")

    blank = tools.execute(ToolCall("search_documents", {"query": "   "}))
    stopwords = tools.execute(ToolCall("search_documents", {"query": "what is it"}))

    assert blank.error
    assert stopwords.error is None
    assert stopwords.result == []


def test_read_document_supports_line_context_and_default_bounded_read(tmp_path: Path):
    knowledge, tools = make_tools(tmp_path)
    (knowledge / "note.md").write_text(
        "\n".join(f"Line {line}" for line in range(1, 47)),
        encoding="utf-8",
    )

    context = tools.execute(
        ToolCall("read_document", {"path": "note.md", "line": 1})
    )
    default = tools.execute(ToolCall("read_document", {"path": "note.md"}))

    assert context.error is None
    assert context.result["start_line"] == 1
    assert context.result["end_line"] == 3
    assert default.result["end_line"] == MAX_READ_LINES
    assert default.result["truncated"] is True


def test_read_document_rejects_partial_invalid_and_too_wide_ranges(tmp_path: Path):
    knowledge, tools = make_tools(tmp_path)
    (knowledge / "note.md").write_text("\n".join(f"Line {n}" for n in range(1, 50)), encoding="utf-8")

    partial = tools.execute(ToolCall("read_document", {"path": "note.md", "start_line": 2}))
    not_integer = tools.execute(
        ToolCall("read_document", {"path": "note.md", "line": "second"})
    )
    boolean = tools.execute(ToolCall("read_document", {"path": "note.md", "line": True}))
    wide = tools.execute(
        ToolCall(
            "read_document",
            {"path": "note.md", "start_line": 1, "end_line": MAX_READ_LINES + 1},
        )
    )

    assert partial.error == "start_line and end_line must be provided together."
    assert not_integer.error == "line must be an integer."
    assert boolean.error == "line must be an integer."
    assert wide.error == f"A read is limited to {MAX_READ_LINES} lines."


def test_read_document_rejects_absolute_paths_hidden_files_and_missing_files(tmp_path: Path):
    knowledge, tools = make_tools(tmp_path)
    (knowledge / ".hidden.md").write_text("hidden", encoding="utf-8")
    absolute = tools.execute(ToolCall("read_document", {"path": str(knowledge / ".hidden.md")}))
    windows_absolute = tools.execute(
        ToolCall("read_document", {"path": "C:\\Users\\private.md"})
    )
    hidden = tools.execute(ToolCall("read_document", {"path": ".hidden.md"}))
    missing = tools.execute(ToolCall("read_document", {"path": "missing.md"}))

    assert absolute.error == "Document path must be relative to the approved folder."
    assert windows_absolute.error == "Document path must be relative to the approved folder."
    assert hidden.error == "Hidden documents are not available to the research tools."
    assert missing.error == "Document does not exist."


def test_read_document_rejects_empty_non_utf8_and_oversized_files(tmp_path: Path):
    knowledge, tools = make_tools(tmp_path)
    (knowledge / "empty.txt").write_text("", encoding="utf-8")
    (knowledge / "bad.txt").write_bytes(b"\xff")
    with (knowledge / "large.md").open("wb") as handle:
        handle.truncate(MAX_FILE_BYTES + 1)

    empty = tools.execute(ToolCall("read_document", {"path": "empty.txt"}))
    bad_encoding = tools.execute(ToolCall("read_document", {"path": "bad.txt"}))
    oversized = tools.execute(ToolCall("read_document", {"path": "large.md"}))

    assert empty.error == "Document is empty."
    assert bad_encoding.error == "Document must use UTF-8 text encoding."
    assert oversized.error == "Document exceeds the 5 MiB file-size limit."


def test_read_and_search_fail_closed_on_symlink_loops(tmp_path: Path):
    knowledge, tools = make_tools(tmp_path)
    loop = knowledge / "loop.md"
    try:
        loop.symlink_to(loop)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks are not available in this environment")

    read = tools.execute(ToolCall("read_document", {"path": "loop.md"}))
    search = tools.execute(ToolCall("search_documents", {"query": "anything"}))

    assert read.error == "Could not resolve document path inside the approved folder."
    assert search.error is None
    assert search.result == []


def test_workspace_constructor_requires_existing_directory(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Knowledge directory does not exist"):
        build_read_only_tools(tmp_path / "does-not-exist")
