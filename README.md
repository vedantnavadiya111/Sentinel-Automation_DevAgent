# Sentinel (Local-First Self-Healing DevOps Agent)
Sentinel is a Docker Compose-based automation project that turns “run this failing command” into an iterative repair loop. It ships an importable n8n workflow that triggers via webhook, executes your command inside an isolated MCP runner, captures errors + file context, requests a full-file rewrite from an LLM, applies the patch deterministically, and re-runs with retries. The stack includes n8n for orchestration, a lightweight “memory” service for recalling prior failures, and Qdrant for vector storage. Language support is designed to cover Python, JavaScript/TypeScript, and Java out of the box via tooling inside the MCP container.





## Prereqs
- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- Docker Compose v2

## Quickstart
1. Copy env file:

   - Windows PowerShell:
     - `Copy-Item .env.example .env`

2. Set `WORKSPACE_PATH` in `.env` to the project folder you want Sentinel to edit.

   Example (Windows):
   - `WORKSPACE_PATH=C:/Users/<you>/code/target_project`

3. Start everything:
- `docker compose up --build`

## Services and Ports
- n8n: `http://localhost:5678`
- Sentinel MCP (streamable HTTP): `http://localhost:8001/mcp`
- Sentinel Memory API: `http://localhost:8002`
- Qdrant: `http://localhost:6333`

## MCP Tools (Sentinel-MCP)
The MCP server exposes 3 tools:
- `read_file(file_path)` → `{ file_path, content }`
- `run_command(command)` → `{ stdout, stderr, exit_code, ... }` (runs inside `/workspace`)
- `apply_patch(file_path, search_text, replace_text)` → Aider-style *single* search/replace

## Memory API (Sentinel Memory)
- `GET /health` → basic health check
- `POST /store` → store an `(error, fix)` pair
- `GET /recall?user_id=...&query=...&limit=5` → retrieve similar past fixes

Notes:
- If Mem0 cannot initialize (e.g., missing `GROQ_API_KEY`), the service falls back to a fully local Qdrant+sentence-transformers store/search.

## n8n Workflow (Guidance)
See [docs/n8n-workflow.md](docs/n8n-workflow.md).

## License / Usage
This repository is **source-available** for viewing, learning, and inspiration.
Redistribution, rehosting, and derivative works are **not permitted** without explicit permission.
See [LICENSE](LICENSE).

This repo scaffolds **Sentinel**, a Docker Compose stack that:
- Runs **n8n** as the orchestration layer
- Exposes a custom **MCP server** (file read/write + command execution) for n8n to call
- Provides a **memory service** backed by **Qdrant**, optionally using **Mem0 OSS**
