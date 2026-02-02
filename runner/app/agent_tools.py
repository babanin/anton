import logging
import os
import subprocess
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file at the given path (relative to repo root).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to repo root"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file at the given path (relative to repo root). Creates parent directories if needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to repo root"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_shell_command",
        "description": "Run a shell command in the repo directory. Returns stdout and stderr.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cmd": {"type": "string", "description": "Shell command to execute"},
            },
            "required": ["cmd"],
        },
    },
    {
        "name": "list_dir",
        "description": "List the contents of a directory (relative to repo root).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path relative to repo root (use '.' for root)"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "git_status",
        "description": "Show the current git status of the repository.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "submit_changes",
        "description": "Call this when you are done making changes. Provide a short summary of what was changed and why.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Summary of changes made"},
            },
            "required": ["summary"],
        },
    },
]


class ToolExecutor:
    def __init__(self, repo_dir: str) -> None:
        self.repo_dir = Path(repo_dir).resolve()

    def execute(self, tool_name: str, tool_input: dict) -> tuple[str, bool]:
        """Execute a tool and return (result_text, is_submit)."""
        try:
            match tool_name:
                case "read_file":
                    return self._read_file(tool_input["path"]), False
                case "write_file":
                    return self._write_file(tool_input["path"], tool_input["content"]), False
                case "run_shell_command":
                    return self._run_shell_command(tool_input["cmd"]), False
                case "list_dir":
                    return self._list_dir(tool_input["path"]), False
                case "git_status":
                    return self._run_shell_command("git status"), False
                case "submit_changes":
                    return tool_input.get("summary", "Changes submitted."), True
                case _:
                    return f"Unknown tool: {tool_name}", False
        except Exception as e:
            logger.exception("Tool %s failed", tool_name)
            return f"Error: {e}", False

    def _resolve(self, path: str) -> Path:
        """Resolve path relative to repo_dir with traversal guard."""
        resolved = (self.repo_dir / path).resolve()
        if not str(resolved).startswith(str(self.repo_dir)):
            raise ValueError(f"Path traversal blocked: {path}")
        return resolved

    def _read_file(self, path: str) -> str:
        resolved = self._resolve(path)
        if not resolved.is_file():
            return f"File not found: {path}"
        content = resolved.read_text(errors="replace")
        if len(content) > 100_000:
            return content[:100_000] + "\n... [truncated at 100k chars]"
        return content

    def _write_file(self, path: str, content: str) -> str:
        resolved = self._resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content)
        return f"Wrote {len(content)} chars to {path}"

    def _run_shell_command(self, cmd: str) -> str:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
                timeout=settings.shell_timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return f"Command timed out after {settings.shell_timeout}s"

        output = result.stdout + result.stderr
        if len(output) > 50_000:
            output = output[:50_000] + "\n... [truncated at 50k chars]"

        if result.returncode != 0:
            return f"Exit code {result.returncode}\n{output}"
        return output or "(no output)"

    def _list_dir(self, path: str) -> str:
        resolved = self._resolve(path)
        if not resolved.is_dir():
            return f"Directory not found: {path}"
        entries = sorted(resolved.iterdir())
        if len(entries) > 500:
            entries = entries[:500]
            truncated = "\n... [truncated at 500 entries]"
        else:
            truncated = ""
        lines = [f"{'d' if e.is_dir() else 'f'}  {e.name}" for e in entries]
        return "\n".join(lines) + truncated
