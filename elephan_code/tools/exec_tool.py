from __future__ import annotations
import shlex
import subprocess
from typing import Any, Dict, List, Optional
from .base_tool import BaseTool, ToolResult


class ExecTool(BaseTool):
    def __init__(self):
        super().__init__("exec_tool")

    def _normalize_command(self, command: Any) -> List[str]:
        if isinstance(command, list):
            return [str(c) for c in command]
        if isinstance(command, str):
            return shlex.split(command)
        raise ValueError("command must be str or list[str]")

    def run(self, **params) -> ToolResult:
        cmd = params.get("command")
        timeout = params.get("timeout", 30)
        cwd = params.get("cwd")
        env = params.get("env")

        if not cmd:
            return ToolResult(success=False, error="Missing 'command' parameter")

        try:
            args = self._normalize_command(cmd)
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=env,
            )

            data = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            success = result.returncode == 0
            return ToolResult(success=success, data=data, exit_code=result.returncode)

        except subprocess.TimeoutExpired as te:
            return ToolResult(success=False, error=f"Timeout: {te}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
