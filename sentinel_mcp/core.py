import os
import subprocess
from pathlib import Path


def workspace_root() -> Path:
    return Path(os.environ.get("WORKSPACE_ROOT", "/workspace")).resolve()


def resolve_in_workspace(file_path: str, root: Path | None = None) -> Path:
    root = (root or workspace_root()).resolve()

    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = root / candidate

    resolved = candidate.resolve()

    if not (resolved == root or resolved.is_relative_to(root)):
        raise ValueError(f"Path must be within {root}: {file_path}")

    return resolved


def read_file_impl(file_path: str, root: Path | None = None) -> dict:
    root = root or workspace_root()
    target = resolve_in_workspace(file_path, root=root)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    text = target.read_text(encoding="utf-8", errors="replace")
    return {"file_path": str(target), "content": text}


def run_command_impl(command: str, root: Path | None = None) -> dict:
    root = (root or workspace_root()).resolve()

    # python:3.x-slim images do not reliably ship with bash.
    shell_executable = "/bin/sh"

    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(root),
        executable=shell_executable,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ},
    )

    return {
        "command": command,
        "cwd": str(root),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
    }


def apply_patch_impl(file_path: str, search_text: str, replace_text: str, root: Path | None = None) -> dict:
    root = root or workspace_root()
    target = resolve_in_workspace(file_path, root=root)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    original = target.read_text(encoding="utf-8", errors="replace")
    occurrences = original.count(search_text)

    if occurrences == 0:
        raise ValueError("search_text not found in file")
    if occurrences > 1:
        raise ValueError(
            f"search_text is ambiguous (found {occurrences} matches). "
            "Provide a longer/more specific search_text block."
        )

    updated = original.replace(search_text, replace_text, 1)
    target.write_text(updated, encoding="utf-8")

    return {
        "file_path": str(target),
        "replaced": True,
        "matches": occurrences,
        "bytes_written": len(updated.encode("utf-8")),
    }
