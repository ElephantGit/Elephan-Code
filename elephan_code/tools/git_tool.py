from __future__ import annotations
import subprocess
from typing import Dict, Any
from .base_tool import BaseTool, ToolResult


class GitTool(BaseTool):
    def __init__(self):
        super().__init__("git_tool")

    def run(self, **params) -> ToolResult:
        cmd = params.get("cmd")
        cwd = params.get("cwd")
        if not cmd:
            return ToolResult(success=False, error="Missing 'cmd' parameter")

        try:
            # cmd can be list or str
            if isinstance(cmd, str):
                args = cmd.split()
            else:
                args = list(cmd)

            result = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
            data = {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
            return ToolResult(success=(result.returncode == 0), data=data, exit_code=result.returncode)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # convenience methods
    def status(self, **params) -> ToolResult:
        return self.run(cmd=["git", "status", "--porcelain"], **params)

    def branch(self, name: str, **params) -> ToolResult:
        return self.run(cmd=["git", "checkout", "-b", name], **params)

    def commit(self, message: str, **params) -> ToolResult:
        return self.run(cmd=["git", "add", "-A"], **params) or self.run(cmd=["git", "commit", "-m", message], **params)
