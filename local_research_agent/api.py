from __future__ import annotations

import os
import uuid
from pathlib import Path, PurePosixPath
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .config import Settings, load_settings
from .core import AgentResult, Citation, Observation, ResearchAgent
from .planner import ExtractivePlanner, OpenAICompatiblePlanner
from .tools import MAX_FILE_BYTES, MAX_READ_CHARS, _safe_document_paths, build_read_only_tools

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_UPLOAD_FILES = 10
MAX_WORKSPACE_BYTES = 50 * 1024 * 1024
MAX_WORKSPACE_DOCUMENTS = 100
_ALLOWED_SUFFIXES = {".md", ".txt", ".text"}
STATIC_DIR = Path(__file__).with_name("static")
SAMPLE_DIR = Path(__file__).with_name("knowledge")


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=3, max_length=1000)
    allow_remote_processing: bool = False


class CitationResponse(BaseModel):
    file: str
    start_line: int
    end_line: int
    quote: str


class TraceItem(BaseModel):
    tool: str
    status: str
    detail: str


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    trace: list[TraceItem]
    stop_reason: str
    model_mode: str
    model_name: str | None


class DocumentInfo(BaseModel):
    path: str
    name: str
    bytes: int
    lines: int | None


def require_ui_request(request: Request) -> None:
    """Reject simple cross-site form submissions to state-changing endpoints."""
    if request.headers.get("x-requested-with") != "LocalResearchAgent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action must come from the Local Research Agent interface.",
        )


def create_app(settings: Settings | None = None, *, seed_samples: bool = True) -> FastAPI:
    app_settings = settings or load_settings()
    knowledge_dir = app_settings.knowledge_dir
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    if seed_samples:
        _initialize_sample_documents(knowledge_dir, SAMPLE_DIR)

    app = FastAPI(
        title="Local Research Agent",
        version="1.0.0",
        description=(
            "A local-first research agent that searches explicitly selected text files, "
            "returns verifiable line citations, and exposes only read-only agent tools."
        ),
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.settings = app_settings
    app.state.knowledge_dir = knowledge_dir

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "base-uri 'none'; form-action 'self'"
        )
        return response

    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "document_count": len(_safe_document_paths(knowledge_dir)),
            "model_mode": app_settings.model_mode,
            "model_name": app_settings.llm_model if app_settings.model_enabled else None,
            "allowed_tools": ["search_documents", "read_document"],
            "max_agent_steps": app_settings.max_agent_steps,
        }

    @app.get("/api/model/status")
    def model_status() -> dict[str, object | None]:
        if not app_settings.model_enabled:
            return {
                "configured": False,
                "mode": "offline",
                "reachable": None,
                "message": "No model is configured; the app is using offline evidence mode.",
            }
        if app_settings.model_is_remote:
            return {
                "configured": True,
                "mode": "remote",
                "reachable": None,
                "message": (
                    "Remote model endpoints are not checked automatically. "
                    "They are contacted only after per-question consent."
                ),
            }

        headers = {}
        if app_settings.llm_api_key:
            headers["Authorization"] = f"Bearer {app_settings.llm_api_key}"
        endpoint = f"{(app_settings.llm_base_url or '').rstrip('/')}/models"
        try:
            response = httpx.get(endpoint, headers=headers, timeout=2.0)
        except httpx.TimeoutException:
            return {
                "configured": True,
                "mode": "local",
                "reachable": False,
                "message": "The local model check timed out. Try again or check that Ollama is running.",
            }
        except httpx.HTTPError:
            return {
                "configured": True,
                "mode": "local",
                "reachable": False,
                "message": (
                    "Could not reach the local model endpoint. Start Ollama and verify the "
                    "OpenAI-compatible URL in .env."
                ),
            }

        if response.is_success:
            return {
                "configured": True,
                "mode": "local",
                "reachable": True,
                "message": "The local model endpoint is reachable.",
            }
        return {
            "configured": True,
            "mode": "local",
            "reachable": False,
            "message": (
                f"The local model endpoint returned HTTP {response.status_code}. "
                "Check Ollama and the /v1 base URL in .env."
            ),
        }

    @app.get("/api/documents", response_model=list[DocumentInfo])
    def list_documents() -> list[DocumentInfo]:
        documents: list[DocumentInfo] = []
        for path in _safe_document_paths(knowledge_dir):
            try:
                relative = path.relative_to(knowledge_dir).as_posix()
                byte_count = path.stat().st_size
                if byte_count <= MAX_FILE_BYTES:
                    text = path.read_text(encoding="utf-8-sig")
                    line_count: int | None = len(text.splitlines())
                else:
                    line_count = None
            except (OSError, UnicodeDecodeError):
                line_count = None
                try:
                    byte_count = path.stat().st_size
                except OSError:
                    continue
                relative = path.relative_to(knowledge_dir).as_posix()
            documents.append(
                DocumentInfo(
                    path=relative,
                    name=Path(relative).name,
                    bytes=byte_count,
                    lines=line_count,
                )
            )
        return documents

    @app.post(
        "/api/documents",
        response_model=list[DocumentInfo],
        dependencies=[Depends(require_ui_request)],
    )
    def upload_documents(
        files: Annotated[list[UploadFile] | None, File()] = None,
    ) -> list[DocumentInfo]:
        if not files:
            raise HTTPException(status_code=400, detail="Choose at least one text document.")
        if len(files) > MAX_UPLOAD_FILES:
            raise HTTPException(
                status_code=413,
                detail=f"Upload at most {MAX_UPLOAD_FILES} files at a time.",
            )

        prepared: list[tuple[str, bytes, int]] = []
        names_in_batch: set[str] = set()
        for upload in files:
            filename = _safe_upload_name(upload.filename or "")
            if filename.casefold() in names_in_batch:
                raise HTTPException(status_code=409, detail="The upload contains duplicate file names.")
            names_in_batch.add(filename.casefold())
            try:
                contents = upload.file.read(MAX_UPLOAD_BYTES + 1)
            finally:
                upload.file.close()
            if len(contents) > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"{filename} exceeds the 5 MiB per-file upload limit.",
                )
            if not contents.strip():
                raise HTTPException(status_code=400, detail=f"{filename} is empty.")
            try:
                contents.decode("utf-8-sig")
            except UnicodeDecodeError as error:
                raise HTTPException(
                    status_code=415,
                    detail=f"{filename} is not UTF-8 text. Save it as UTF-8 and try again.",
                ) from error
            prepared.append((filename, contents, len(contents.splitlines())))

        existing = _safe_document_paths(knowledge_dir)
        existing_names = {path.relative_to(knowledge_dir).as_posix().casefold() for path in existing}
        if any(name.casefold() in existing_names for name, _, _ in prepared):
            raise HTTPException(
                status_code=409,
                detail="A document with that name already exists. Rename the file and upload again.",
            )
        existing_bytes = sum(path.stat().st_size for path in existing if path.exists())
        new_bytes = sum(len(contents) for _, contents, _ in prepared)
        if len(existing) + len(prepared) > MAX_WORKSPACE_DOCUMENTS:
            raise HTTPException(
                status_code=413,
                detail=f"The knowledge folder is limited to {MAX_WORKSPACE_DOCUMENTS} documents.",
            )
        if existing_bytes + new_bytes > MAX_WORKSPACE_BYTES:
            raise HTTPException(status_code=413, detail="The knowledge folder is limited to 50 MiB.")

        created: list[Path] = []
        temporary: list[Path] = []
        try:
            for filename, contents, _ in prepared:
                temporary_path = knowledge_dir / f".upload-{uuid.uuid4().hex}.tmp"
                temporary.append(temporary_path)
                temporary_path.write_bytes(contents)
                destination = knowledge_dir / filename
                if destination.exists():
                    raise HTTPException(status_code=409, detail="A document with that name already exists.")
                os.replace(temporary_path, destination)
                created.append(destination)
        except HTTPException:
            for path in created:
                path.unlink(missing_ok=True)
            raise
        except OSError as error:
            for path in created:
                path.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail="Could not store the selected documents.") from error
        finally:
            for path in temporary:
                path.unlink(missing_ok=True)

        return [
            DocumentInfo(
                path=filename,
                name=filename,
                bytes=len(contents),
                lines=line_count,
            )
            for filename, contents, line_count in prepared
        ]

    @app.delete(
        "/api/documents/{document_path:path}",
        dependencies=[Depends(require_ui_request)],
    )
    def delete_document(document_path: str) -> dict[str, str]:
        normalized = document_path.replace("\\", "/")
        if not normalized or any(part in {"", ".", ".."} for part in normalized.split("/")):
            raise HTTPException(status_code=400, detail="Invalid document path.")
        try:
            target = (knowledge_dir / normalized).resolve()
        except (OSError, RuntimeError):
            raise HTTPException(status_code=404, detail="Document not found.") from None
        if not target.is_relative_to(knowledge_dir) or target.suffix.casefold() not in _ALLOWED_SUFFIXES:
            raise HTTPException(status_code=404, detail="Document not found.")
        if not target.is_file():
            raise HTTPException(status_code=404, detail="Document not found.")
        try:
            target.unlink()
        except OSError as error:
            raise HTTPException(status_code=500, detail="Could not remove the selected document.") from error
        return {"status": "removed", "path": normalized}

    @app.post(
        "/api/ask",
        response_model=AskResponse,
        dependencies=[Depends(require_ui_request)],
    )
    def ask(body: AskRequest) -> AskResponse:
        if app_settings.model_is_remote and not body.allow_remote_processing:
            raise HTTPException(
                status_code=428,
                detail=(
                    "This request would send your question and retrieved passages to a remote model. "
                    "Review the privacy note and explicitly allow remote processing first."
                ),
            )

        if app_settings.model_enabled:
            planner = OpenAICompatiblePlanner(
                base_url=app_settings.llm_base_url or "",
                model=app_settings.llm_model or "",
                api_key=app_settings.llm_api_key,
                timeout_seconds=app_settings.llm_timeout_seconds,
            )
        else:
            planner = ExtractivePlanner()

        agent = ResearchAgent(
            planner,
            build_read_only_tools(knowledge_dir),
            max_steps=app_settings.max_agent_steps,
        )
        try:
            result = agent.run(body.question)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        answer = result.answer
        citations = _citation_responses(result.citations, result.observations)
        if app_settings.model_enabled:
            had_read_evidence = any(
                item.tool_name == "read_document" and not item.error
                for item in result.observations
            )
            had_search_hits = any(
                item.tool_name == "search_documents"
                and isinstance(item.result, list)
                and bool(item.result)
                for item in result.observations
            )
            if (
                (had_read_evidence or had_search_hits)
                and not citations
                and result.stop_reason != "ungrounded_answer"
            ):
                answer = (
                    "I withheld the model response because it did not return a citation "
                    "that could be verified against the passages read. Please try again."
                )

        if citations:
            sources = "\n".join(
                f"- [{item.file}, lines {item.start_line}-{item.end_line}]"
                for item in citations
            )
            if "Sources:" not in answer:
                answer = f"{answer.rstrip()}\n\nSources:\n{sources}"

        return AskResponse(
            answer=answer,
            citations=citations,
            trace=_trace_items(result),
            stop_reason=result.stop_reason,
            model_mode=app_settings.model_mode,
            model_name=app_settings.llm_model if app_settings.model_enabled else None,
        )

    return app


def _initialize_sample_documents(knowledge_dir: Path, sample_dir: Path) -> None:
    marker = knowledge_dir / ".samples-initialized"
    if marker.exists():
        return
    has_documents = bool(_safe_document_paths(knowledge_dir))
    if not has_documents and sample_dir.is_dir():
        for sample in sorted(sample_dir.glob("*.md")):
            destination = knowledge_dir / sample.name
            if not destination.exists():
                destination.write_bytes(sample.read_bytes())
    marker.write_text("Local Research Agent workspace initialized.\n", encoding="utf-8")


def _safe_upload_name(raw_name: str) -> str:
    basename = PurePosixPath(raw_name.replace("\\", "/")).name
    if not basename or basename in {".", ".."} or basename.startswith("."):
        raise HTTPException(status_code=400, detail="Hidden or invalid file names are not accepted.")
    suffix = Path(basename).suffix.casefold()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Only .md, .txt, and .text files are supported.")
    stem = Path(basename).stem
    safe_stem = "".join(char if char.isalnum() or char in "-_" else "_" for char in stem)
    safe_stem = safe_stem.strip("_-.")[:100] or "document"
    windows_reserved = {
        "con", "prn", "aux", "nul",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
    }
    if safe_stem.casefold() in windows_reserved:
        safe_stem = f"document_{safe_stem}"
    return f"{safe_stem}{suffix}"


def _citation_responses(
    citations: tuple[Citation, ...],
    observations: tuple[Observation, ...],
) -> list[CitationResponse]:
    output: list[CitationResponse] = []
    for citation in citations:
        for observation in observations:
            if observation.tool_name != "read_document" or observation.error:
                continue
            result = observation.result
            if not isinstance(result, dict) or result.get("path") != citation.path:
                continue
            start = result.get("start_line")
            end = result.get("end_line")
            content = result.get("content")
            if (
                isinstance(start, int)
                and isinstance(end, int)
                and isinstance(content, str)
                and citation.start_line >= start
                and citation.end_line <= end
            ):
                output.append(
                    CitationResponse(
                        file=citation.path,
                        start_line=citation.start_line,
                        end_line=citation.end_line,
                        quote=content[:MAX_READ_CHARS],
                    )
                )
                break
    return output


def _trace_items(result: AgentResult) -> list[TraceItem]:
    trace: list[TraceItem] = []
    for observation in result.observations:
        if observation.error:
            detail = observation.error
            blocked_terms = ("not registered", "escapes", "must be returned", "must search")
            state = "blocked" if any(term in detail.casefold() for term in blocked_terms) else "error"
        elif observation.tool_name == "search_documents":
            count = len(observation.result) if isinstance(observation.result, list) else 0
            detail = f"Found {count} relevant passage(s) in the approved folder."
            state = "ok"
        elif observation.tool_name == "read_document" and isinstance(observation.result, dict):
            path = observation.result.get("path", "document")
            first = observation.result.get("start_line", "?")
            last = observation.result.get("end_line", "?")
            detail = f"Read {path}, lines {first}-{last}."
            state = "ok"
        else:
            detail = "Tool completed."
            state = "ok"
        trace.append(TraceItem(tool=observation.tool_name, status=state, detail=detail))
    return trace


app = create_app()
