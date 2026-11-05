from pathlib import Path

from .core import ToolError, ToolRegistry

MAX_SEARCH_RESULTS = 5
MAX_READ_LINES = 80
MAX_READ_CHARS = 4000


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


def _required_text(arguments: dict[str, str], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ToolError(f"Missing required argument: {name}")
    return value.strip()


def _search_documents(root: Path, arguments: dict[str, str]) -> list[dict[str, object]]:
    query = _required_text(arguments, "query")
    if len(query) > 120:
        raise ToolError("Search query is too long.")

    matches: list[dict[str, object]] = []
    for file_path in sorted(root.rglob("*.md")):
        safe_path = file_path.resolve()
        if not safe_path.is_relative_to(root):
            continue
        try:
            lines = safe_path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise ToolError("Could not read a local Markdown document.") from error

        for line_number, line in enumerate(lines, start=1):
            if query.casefold() not in line.casefold():
                continue
            matches.append(
                {
                    "path": safe_path.relative_to(root).as_posix(),
                    "line": line_number,
                    "snippet": line.strip()[:220],
                }
            )
            if len(matches) >= MAX_SEARCH_RESULTS:
                return matches

    return matches


def _read_document(root: Path, arguments: dict[str, str]) -> dict[str, object]:
    relative_path = _required_text(arguments, "path")
    safe_path = (root / relative_path).resolve()
    if not safe_path.is_relative_to(root):
        raise ToolError("Document path escapes the knowledge directory.")
    if safe_path.suffix.lower() != ".md":
        raise ToolError("Only Markdown documents can be read.")
    if not safe_path.is_file():
        raise ToolError("Document does not exist.")

    try:
        lines = safe_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ToolError("Could not read the local Markdown document.") from error

    requested_line = arguments.get("line")
    if requested_line:
        try:
            line_number = int(requested_line)
        except ValueError as error:
            raise ToolError("Line number must be an integer.") from error
        if line_number < 1 or line_number > len(lines):
            raise ToolError("Line number is outside the document.")
        start_line = max(1, line_number - 2)
        end_line = min(len(lines), line_number + 2)
    else:
        start_line = 1
        end_line = min(len(lines), MAX_READ_LINES)

    content = "\n".join(
        f"{current_line}: {lines[current_line - 1]}"
        for current_line in range(start_line, end_line + 1)
    )
    truncated = end_line < len(lines) or len(content) > MAX_READ_CHARS
    content = content[:MAX_READ_CHARS]

    return {
        "path": safe_path.relative_to(root).as_posix(),
        "start_line": start_line,
        "end_line": end_line,
        "content": content,
        "truncated": truncated,
    }
