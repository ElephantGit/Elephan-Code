from __future__ import annotations
import subprocess
from typing import Dict, Any, List
from .base_tool import BaseTool, ToolResult, ToolSchema, ToolParameter


class GitTool(BaseTool):
    def __init__(self):
        super().__init__("git_tool")
        self._schema = ToolSchema(
            name="git_tool",
            description="Execute git commands for version control operations",
            parameters=[
                ToolParameter(
                    name="cmd",
                    type="string",
                    description="Git command to execute (e.g., 'git status', 'git diff')",
                    required=True,
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="Working directory for the git command",
                    required=False,
                ),
            ],
        )

    def run(self, **params) -> ToolResult:
        cmd = params.get("cmd")
        cwd = params.get("cwd")
        if not cmd:
            return ToolResult(success=False, error="Missing 'cmd' parameter")

        try:
            if isinstance(cmd, str):
                args = cmd.split()
            else:
                args = list(cmd)

            result = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
            data = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            return ToolResult(
                success=(result.returncode == 0), data=data, exit_code=result.returncode
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def status(self, **params) -> ToolResult:
        return self.run(cmd=["git", "status", "--porcelain"], **params)

    def branch(self, name: str, **params) -> ToolResult:
        return self.run(cmd=["git", "checkout", "-b", name], **params)

    def commit(self, message: str, **params) -> ToolResult:
        add_result = self.run(cmd=["git", "add", "-A"], **params)
        if not add_result.success:
            return add_result
        return self.run(cmd=["git", "commit", "-m", message], **params)
