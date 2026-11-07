# Portfolio summary — Local Research Agent

**One-line description:** Built a local-first research agent that searches user-selected documents, calls a constrained read-only toolset, and returns answers with line-validated citations.

**Resume bullet (edit to match your own experience):**

> Designed and implemented a local-first research agent with a FastAPI web UI, ranked text retrieval, structured tool-calling integration, a bounded agent loop, and citation validation. Added file-sandbox controls, explicit consent for remote model processing, an offline extractive mode, API/security regression tests, CI, and a small Hit@k/MRR retrieval evaluation.

**Demonstrable features:** upload text/Markdown files; ask a question; inspect evidence quotes and line citations; expand the tool trace; run with no model or configure a local/remote OpenAI-compatible tool-calling model.

**What this does not claim:** production multi-user security, semantic retrieval quality, or formal security certification. The included retrieval evaluation has six annotated sample questions and should be expanded before making broad quality claims.
