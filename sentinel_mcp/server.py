import contextlib
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.routing import Mount
import uvicorn

from mcp.server.fastmcp import FastMCP

from sentinel_mcp.core import apply_patch_impl, read_file_impl, run_command_impl, workspace_root

mcp = FastMCP(
    name="Sentinel-MCP",
    instructions=(
        "Tools for reading/editing files and running commands inside the mounted /workspace. "
        "All file paths must stay within the workspace root."
    ),
    stateless_http=True,
    json_response=True,
)


class RunCommandRequest(BaseModel):
    command: str


class ApplyPatchRequest(BaseModel):
    file_path: str
    search_text: str
    replace_text: str


class ReadFileRequest(BaseModel):
    file_path: str


def _resolve_in_workspace(file_path: str) -> Path:
    # Back-compat shim (older tests / integrations may call this helper).
    from sentinel_mcp.core import resolve_in_workspace

    return resolve_in_workspace(file_path, root=workspace_root())


@mcp.tool()
def read_file(file_path: str) -> dict:
    """Return the UTF-8 text content of a file under /workspace."""
    return read_file_impl(file_path, root=workspace_root())


@mcp.tool()
def run_command(command: str) -> dict:
    """Execute a shell command in /workspace and capture stdout/stderr/exit_code."""
    return run_command_impl(command, root=workspace_root())


@mcp.tool()
def apply_patch(file_path: str, search_text: str, replace_text: str) -> dict:
    """Aider-style edit: replace exactly one occurrence of search_text with replace_text."""
    return apply_patch_impl(file_path, search_text, replace_text, root=workspace_root())


def main() -> None:
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8001"))

    # REST shim for n8n (simple HTTP requests) + MCP mounted at /mcp.
    api = FastAPI(title="Sentinel MCP Bridge", version="0.1.0")

    @api.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @api.post("/run_command")
    def run_command_http(req: RunCommandRequest) -> dict:
        return run_command_impl(req.command, root=workspace_root())

    @api.post("/apply_patch")
    def apply_patch_http(req: ApplyPatchRequest) -> dict:
        try:
            return apply_patch_impl(req.file_path, req.search_text, req.replace_text, root=workspace_root())
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @api.post("/read_file")
    def read_file_http(req: ReadFileRequest) -> dict:
        try:
            return read_file_impl(req.file_path, root=workspace_root())
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Mount MCP Streamable HTTP under /mcp for clients that speak MCP.
    # FastMCP provides a Starlette app for streamable HTTP.
    mcp_app = mcp.streamable_http_app()
    api.router.routes.append(Mount("/mcp", app=mcp_app))

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI):
        async with mcp.session_manager.run():
            yield

    api.router.lifespan_context = lifespan  # type: ignore[attr-defined]

    uvicorn.run(api, host=host, port=port)


if __name__ == "__main__":
    main()
