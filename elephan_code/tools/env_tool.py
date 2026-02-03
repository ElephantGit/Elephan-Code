from __future__ import annotations
import subprocess
import json
from typing import Any, Dict
from .base_tool import BaseTool, ToolResult


class EnvTool(BaseTool):
    def __init__(self):
        super().__init__("env_tool")

    def run(self, **params) -> ToolResult:
        action = params.get("action")
        if action == "check_deps":
            return self.check_deps(**params)
        if action == "list_env":
            return self.list_env(**params)
        return ToolResult(success=False, error="Unknown action")

    def check_deps(self, **params) -> ToolResult:
        # run `pip list --format=json`
        try:
            result = subprocess.run(["pip", "list", "--format=json"], capture_output=True, text=True)
            if result.returncode != 0:
                return ToolResult(success=False, error=result.stderr)
            data = json.loads(result.stdout)
            return ToolResult(success=True, data=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def list_env(self, **params) -> ToolResult:
        # basic env info
        try:
            import sys
            data = {"python_version": sys.version, "executable": sys.executable}
            return ToolResult(success=True, data=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
