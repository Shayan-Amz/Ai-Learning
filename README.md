# Local Research Agent

A local-first research agent that searches only the text documents you explicitly add, reads bounded passages, and returns answers with verifiable file-and-line citations. It is designed as a small, inspectable agent system—not a black-box chatbot.

> **Default mode is offline.** No model key, cloud account, or network connection is required to run the app. An optional OpenAI-compatible planner can use a local Ollama model or a remote provider; remote processing is disabled per request unless the user explicitly consents in the UI.

## What it does

- **Explicit document selection:** upload `.md`, `.txt`, and `.text` files in the browser; the app does not crawl your home folder or follow links to arbitrary locations.
- **Ranked local retrieval:** uses a small BM25-style lexical ranker, expands a matched Markdown topic heading to its bounded section, and preserves original line ranges.
- **Agent loop:** goal → planner action → allow-listed tool → observation → next action or finish, with a configurable hard step limit.
- **Evidence-grounded output:** citations must match successful reads, and each model-answer sentence must also match the cited passage's key terms and an in-order phrase. When question and evidence languages differ, the model is instructed to preserve the source language rather than make an unsupported translation. After a failed check, the agent gets one bounded chance to search/read other evidence and requires another read when an unread hit is available; if that also fails, the answer is withheld. The offline planner returns retrieved evidence instead of inventing a summary.
- **Optional tool-calling model:** an OpenAI-compatible chat-completions endpoint may choose `search_documents`, `read_document`, and `finish`. The registry still refuses every unregistered tool.
- **Privacy-aware model use:** Ollama on loopback is classified as local. A remote HTTPS model needs a per-question consent checkbox; only the question and retrieved excerpts are sent.
- **Read-only agent permissions:** the agent has no shell, filesystem-write, delete, email, payment, or general network tool. Adding/removing documents is a separate, explicit UI operation; removing one requires confirmation.
- **Safe-by-default workspace:** selected documents are stored in the ignored `.local_data/` directory. Chat messages are not persisted by the app, and secrets belong in ignored `.env` files.
- **Retrieval evaluation:** a small, checked-in query set reports Hit@k and MRR so retrieval changes can be measured rather than guessed.

## Windows quick start (PowerShell)

Open PowerShell in the repository root (the folder containing `README.md`). These commands use a project-local virtual environment and do not change your global Python installation:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m local_research_agent.server
```

- `py -3 -m venv .venv` creates an isolated Python environment in `.venv`.
- The second line installs the app's runtime packages into that environment.
- The third line starts the local web app; by default it listens only on `127.0.0.1:8000`.

Open **http://127.0.0.1:8000**. The first run copies two small, public sample notes into `.local_data/knowledge/` so the app is immediately usable. Add your own `.md`, `.txt`, or `.text` files with **Add documents**. They remain in your local workspace until you remove them in the app or delete that workspace yourself.

If the `py` launcher is not installed, use `python -m venv .venv` in its place. If port `8000` is occupied, set `LOCAL_RESEARCH_PORT` in `.env` before starting the server.

## Optional model setup

The app works without a model. For line-by-line Windows/Ollama setup and troubleshooting, see [`docs/local-ollama-setup-fa.md`](docs/local-ollama-setup-fa.md). To enable structured tool calling with local Ollama, install Ollama, download a model that supports tools, then create a local `.env` from the example:

```powershell
Copy-Item .env.example .env
notepad .env
```

- `Copy-Item` creates a private local settings file; `.env` is ignored by Git.
- `notepad .env` opens it so you can set the base URL and model name. For Ollama's OpenAI-compatible endpoint, the settings look like this:

```text
LOCAL_RESEARCH_LLM_BASE_URL=http://127.0.0.1:11434/v1
LOCAL_RESEARCH_LLM_MODEL=your-tool-capable-ollama-model
```

Restart the app after editing `.env`. A loopback model runs locally. For a remote provider, use its HTTPS base URL and set `LOCAL_RESEARCH_LLM_API_KEY` in `.env`; never commit or share that file. The UI will disclose remote processing and requires you to check a consent box for each question. The provider receives your question and the passages the agent retrieved, not the whole library.

## Tests and retrieval evaluation

Install the development tools once, then run the full suite and the retrieval evaluation:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m ruff check local_research_agent tests
.\.venv\Scripts\python.exe -m pytest --cov=local_research_agent --cov-report=term-missing
.\.venv\Scripts\python.exe -m local_research_agent.evaluate --k 5
```

The test suite covers the agent loop, ranked search, citation and answer-grounding checks, traversal and symlink boundaries, upload validation, state-changing request protection, model consent, tool-calling response parsing, and safe stopping. The evaluation set is deliberately small and transparent; it is a regression check, not a claim of general retrieval quality.

## Architecture

```text
Browser UI (same origin)
  ├─ explicit upload/list/remove actions ──> FastAPI document workspace (.local_data/knowledge)
  └─ question + optional consent ─────────> ResearchAgent
                                               ├─ Planner: offline evidence mode or OpenAI-compatible tool caller
                                               ├─ ToolRegistry: search_documents, read_document only
                                               └─ Observations → citation validation → answer + trace
```

| Area | Files | Responsibility |
|---|---|---|
| Agent contracts and loop | `local_research_agent/core.py` | Actions, observations, bounded steps, search-before-read policy, citation verification |
| Retrieval and file safety | `local_research_agent/tools.py` | Ranked search, UTF-8/size limits, line-preserving reads, path/symlink checks |
| Planners | `local_research_agent/planner.py` | Offline extractive planning and structured OpenAI-compatible tool calls |
| Web API and configuration | `local_research_agent/api.py`, `config.py`, `server.py` | FastAPI endpoints, local workspace, privacy consent, local server settings |
| User interface | `local_research_agent/static/` | Responsive document library, research view, citations, and tool trace |
| Tests/evaluation | `tests/`, `local_research_agent/evaluation_set.json` | Safety, API, model contract, and retrieval regression checks |

API documentation is available at **http://127.0.0.1:8000/api/docs** while the server is running.

## Safety and privacy boundaries

- Only `.md`, `.txt`, and `.text` files inside the workspace are searchable; uploads are UTF-8 validated and bounded by file, count, and total-workspace limits.
- Search paths are canonicalized. Traversal, hidden files, unsupported extensions, and symlinks outside the approved workspace are refused.
- A `read_document` call is authorized only after a successful search has returned that document.
- A final answer with retrieved evidence must cite exact line ranges returned by `read_document`. Citation ranges and sentence-level lexical/phrase grounding are checked; unsupported claims or citations cause the answer to be withheld.
- The document content is treated as untrusted evidence, never as a source of tool permissions. The agent tool registry cannot write, delete, execute code, or make arbitrary network requests.
- Remote model use is explicit and per-request. A non-local model endpoint must use HTTPS. The model key is never included in API status output or application logs.
- This is a single-user local application, not a hardened multi-user service. Keep the default loopback binding; do not expose it to a public network. For a remote model, read that provider's data-retention terms before using sensitive documents.

## Current limitations

- Only Markdown and UTF-8 plain text are accepted. PDF/OCR, Office formats, semantic embeddings, persistent chat history, and multi-user accounts are intentionally out of scope.
- The offline planner retrieves and quotes evidence; it does not compose a natural-language synthesis. An optional tool-capable model can synthesize, but the grounding gate is a conservative lexical/phrase check—not a full semantic entailment proof. Review the displayed source text, especially for technical explanations or important decisions.
- The included evaluation set has six examples over two sample notes. It is useful for regressions, not a broad benchmark.

## Project and learning notes

For a concise, truthful portfolio description and resume bullet, see [`docs/portfolio-summary-en.md`](docs/portfolio-summary-en.md). Current Persian references are `docs/agent-architecture-fa.md`, `docs/safety-review-fa.md`, `docs/evaluation-fa.md`, and `docs/agent-capstone-fa.md`. Lessons 16–18 describe the current implementation; earlier lessons and Pathfinder documents are retained as historical learning/prototype notes.

## Historical prototype

`backend/` and `frontend/` contain a previous Pathfinder Canada program-explorer prototype. It is retained as historical work, is not part of this Agent's runtime, and is not the current project goal.
