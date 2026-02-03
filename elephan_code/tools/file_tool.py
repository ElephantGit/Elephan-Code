from __future__ import annotations
import os
import shutil
from typing import Any
from .base_tool import BaseTool, ToolResult


class FileTool(BaseTool):
    def __init__(self):
        super().__init__("file_tool")

    def run(self, **params) -> ToolResult:
        # 支持两个操作：read 和 write，通过 action 参数或参数自动判断
        action = params.get("action")
        if not action:
            # backward compatible: if path and content present -> write else read
            if "content" in params:
                action = "write"
            else:
                action = "read"

        path = params.get("path")
        if not path:
            return ToolResult(success=False, error="Missing 'path' parameter")

        try:
            if action == "read":
                with open(path, 'r', encoding='utf-8') as f:
                    data = f.read()
                return ToolResult(success=True, data=data)

            elif action == "write":
                content = params.get("content", "")
                # create backup
                if os.path.exists(path):
                    backup = path + ".bak"
                    shutil.copy2(path, backup)
                # atomic write via temp file
                tmp_path = path + ".tmp"
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                os.replace(tmp_path, path)
                return ToolResult(success=True, data="File write successfully.")

            else:
                return ToolResult(success=False, error=f"Unsupported file action: {action}")

        except Exception as e:
            return ToolResult(success=False, error=str(e))
