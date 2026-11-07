from __future__ import annotations

import errno
import math
import re
from collections import Counter
from pathlib import Path, PureWindowsPath

from .core import ToolError, ToolRegistry

MAX_SEARCH_RESULTS = 5
MAX_SEARCH_DOCUMENTS = 100
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_SEARCH_TOTAL_BYTES = 50 * 1024 * 1024
MAX_READ_LINES = 40
MAX_READ_CHARS = 6000
CHUNK_LINES = 6
CHUNK_OVERLAP = 2
_ALLOWED_SUFFIXES = {".md", ".txt"}
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but",
    "by", "can", "could", "do", "does", "for", "from", "had", "has", "have",
    "how", "i", "if", "in", "into", "is", "it", "its", "me", "my", "of",
    "on", "or", "our", "please", "should", "that", "the", "their", "them",
    "there", "these", "they", "this", "to", "was", "we", "were", "what",
    "when", "where", "which", "who", "why", "will", "with", "would", "you",
    "your", "find", "tell", "show", "local", "document", "documents", "note",
    "notes", "about",
}


def build_read_only_tools(knowledge_dir: Path) -> ToolRegistry:
    root = knowledge_dir.resolve()
    if not root.is_dir():
        raise FileNotFoundError("Knowledge directory does not exist.")

    return ToolRegistry(
        {
            "search_documents": lambda arguments: _search_documents(root, arguments),
            "read_document": lambda arguments: _read_document(root, arguments),
        }
    )


def _required_text(arguments: dict[str, object], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ToolError(f"Missing or invalid required argument: {name}")
    return value.strip()


def _integer_argument(arguments: dict[str, object], name: str) -> int | None:
    value = arguments.get(name)
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ToolError(f"{name} must be an integer.")
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ToolError(f"{name} must be an integer.") from error


def _tokens(text: str) -> list[str]:
    raw_tokens = re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE)
    tokens: list[str] = []
    for token in raw_tokens:
        if token in _STOP_WORDS:
            continue
        if len(token) > 5 and token.endswith("ies"):
            token = token[:-3] + "y"
        elif len(token) > 5 and token.endswith("ing"):
            token = token[:-3]
        elif len(token) > 4 and token.endswith("ed"):
            token = token[:-2]
        elif len(token) > 4 and token.endswith("s"):
            token = token[:-1]
        if len(token) > 6 and token.endswith("al"):
            token = token[:-2]
        if token:
            tokens.append(token)
    return tokens


def _safe_document_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(root.rglob("*")):
        try:
            relative = path.relative_to(root)
            resolved = path.resolve()
        except (OSError, RuntimeError, ValueError):
            continue
        if any(part.startswith(".") for part in relative.parts):
            continue
        if not resolved.is_relative_to(root) or not resolved.is_file():
            continue
        if resolved.suffix.casefold() not in _ALLOWED_SUFFIXES:
            continue
        paths.append(resolved)
        if len(paths) >= MAX_SEARCH_DOCUMENTS:
            break
    return paths


def _read_utf8(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ToolError("Document exceeds the 5 MiB file-size limit.")
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise ToolError("Document must use UTF-8 text encoding.") from error
    except OSError as error:
        raise ToolError("Could not read a local text document.") from error


def _make_chunks(text: str) -> list[tuple[int, int, str]]:
    lines = text.splitlines()
    chunks: list[tuple[int, int, str]] = []
    if not lines:
        return chunks

    start_index = 0
    while start_index < len(lines):
        end_index = min(len(lines), start_index + CHUNK_LINES)
        chunk_text = "\n".join(lines[start_index:end_index]).strip()
        if chunk_text:
            chunks.append((start_index + 1, end_index, chunk_text))
        if end_index == len(lines):
            break
        start_index = end_index - CHUNK_OVERLAP
    return chunks


def _search_documents(root: Path, arguments: dict[str, object]) -> list[dict[str, object]]:
    query = _required_text(arguments, "query")
    if len(query) > 1000:
        raise ToolError("Search query is too long.")
    query_tokens = _tokens(query)
    if not query_tokens:
        return []

    chunks: list[dict[str, object]] = []
    total_bytes = 0
    for file_path in _safe_document_paths(root):
        try:
            relative_path = file_path.relative_to(root).as_posix()
            file_size = file_path.stat().st_size
        except (OSError, ValueError):
            continue
        total_bytes += file_size
        if total_bytes > MAX_SEARCH_TOTAL_BYTES:
            raise ToolError("The approved knowledge folder exceeds the 50 MiB search limit.")
        text = _read_utf8(file_path)
        for start_line, end_line, chunk_text in _make_chunks(text):
            tokens = _tokens(chunk_text)
            if tokens:
                chunks.append(
                    {
                        "path": relative_path,
                        "start_line": start_line,
                        "end_line": end_line,
                        "text": chunk_text,
                        "tokens": tokens,
                        "frequencies": Counter(tokens),
                    }
                )

    if not chunks:
        return []

    document_frequency: Counter[str] = Counter()
    for chunk in chunks:
        document_frequency.update(set(chunk["tokens"]))
    average_length = sum(len(chunk["tokens"]) for chunk in chunks) / len(chunks)
    average_length = max(average_length, 1.0)
    query_terms = set(query_tokens)
    phrase = " ".join(query_tokens)
    scored: list[tuple[float, dict[str, object]]] = []

    for chunk in chunks:
        frequencies = chunk["frequencies"]
        length = len(chunk["tokens"])
        score = 0.0
        for term in query_terms:
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            frequency_in_chunks = document_frequency[term]
            inverse_document_frequency = math.log(
                1.0 + (len(chunks) - frequency_in_chunks + 0.5) / (frequency_in_chunks + 0.5)
            )
            denominator = frequency + 1.5 * (1.0 - 0.75 + 0.75 * length / average_length)
            score += inverse_document_frequency * frequency * 2.5 / denominator
        normalized_text = " ".join(chunk["tokens"])
        if phrase and phrase in normalized_text:
            score += 1.0
        if score > 0:
            scored.append((score, chunk))

    scored.sort(
        key=lambda item: (
            -item[0],
            str(item[1]["path"]).casefold(),
            int(item[1]["start_line"]),
        )
    )
    results: list[dict[str, object]] = []
    for score, chunk in scored:
        path = str(chunk["path"])
        start_line = int(chunk["start_line"])
        end_line = int(chunk["end_line"])
        overlaps_existing = any(
            existing["path"] == path
            and start_line <= int(existing["end_line"])
            and end_line >= int(existing["start_line"])
            for existing in results
        )
        if overlaps_existing:
            continue
        snippet = str(chunk["text"]).strip()
        results.append(
            {
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
                "line": start_line,
                "snippet": snippet[:600],
                "score": round(score, 4),
            }
        )
        if len(results) >= MAX_SEARCH_RESULTS:
            break
    return results


def _read_document(root: Path, arguments: dict[str, object]) -> dict[str, object]:
    relative_path = _required_text(arguments, "path").replace("\\", "/")
    if Path(relative_path).is_absolute() or PureWindowsPath(relative_path).is_absolute():
        raise ToolError("Document path must be relative to the approved folder.")
    relative_parts = Path(relative_path).parts
    try:
        safe_path = (root / relative_path).resolve()
    except (OSError, RuntimeError) as error:
        raise ToolError("Could not resolve document path inside the approved folder.") from error
    if not safe_path.is_relative_to(root):
        raise ToolError("Document path escapes the approved folder.")
    if any(part.startswith(".") for part in relative_parts):
        raise ToolError("Hidden documents are not available to the research tools.")
    if safe_path.suffix.casefold() not in _ALLOWED_SUFFIXES:
        raise ToolError("Only Markdown and plain-text documents can be read.")
    try:
        safe_path.stat()
    except OSError as error:
        if error.errno == getattr(errno, "ELOOP", -1):
            raise ToolError("Could not resolve document path inside the approved folder.") from error
        if error.errno in {errno.ENOENT, errno.ENOTDIR}:
            raise ToolError("Document does not exist.") from error
        raise ToolError("Could not read a local text document.") from error
    if not safe_path.is_file():
        raise ToolError("Document does not exist.")

    text = _read_utf8(safe_path)
    lines = text.splitlines()
    if not lines:
        raise ToolError("Document is empty.")

    start_line = _integer_argument(arguments, "start_line")
    end_line = _integer_argument(arguments, "end_line")
    line = _integer_argument(arguments, "line")
    if (start_line is None) != (end_line is None):
        raise ToolError("start_line and end_line must be provided together.")
    if start_line is not None and end_line is not None:
        first_line, last_line = start_line, end_line
    elif line is not None:
        first_line, last_line = max(1, line - 2), min(len(lines), line + 2)
    else:
        first_line, last_line = 1, min(len(lines), MAX_READ_LINES)

    if first_line < 1 or last_line < first_line or last_line > len(lines):
        raise ToolError("Requested line range is outside the document.")
    if last_line - first_line + 1 > MAX_READ_LINES:
        raise ToolError(f"A read is limited to {MAX_READ_LINES} lines.")

    numbered_lines = [
        f"{current_line}: {lines[current_line - 1]}"
        for current_line in range(first_line, last_line + 1)
    ]
    content = "\n".join(numbered_lines)
    truncated = first_line > 1 or last_line < len(lines) or len(content) > MAX_READ_CHARS
    actual_end_line = last_line
    if len(content) > MAX_READ_CHARS:
        content = content[:MAX_READ_CHARS]
        actual_end_line = min(last_line, first_line + len(content.splitlines()) - 1)

    return {
        "path": safe_path.relative_to(root).as_posix(),
        "start_line": first_line,
        "end_line": actual_end_line,
        "content": content,
        "truncated": truncated,
    }
