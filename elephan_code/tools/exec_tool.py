from __future__ import annotations
import shlex
import subprocess
import re
from typing import Any, Dict, List, Optional, Set
from .base_tool import BaseTool, ToolResult, ToolSchema, ToolParameter


DANGEROUS_PATTERNS: List[str] = [
    r"rm\s+(-[rfRF]+\s+)?/",
    r"rm\s+(-[rfRF]+\s+)?\*",
    r"mkfs\.",
    r"dd\s+.*of=/dev/",
    r">\s*/dev/sd",
    r"chmod\s+(-[rR]+\s+)?777\s+/",
    r"chown\s+.*\s+/",
    r":()\{.*\|.*&\s*\};:",
    r"curl.*\|\s*(ba)?sh",
    r"wget.*\|\s*(ba)?sh",
    r"eval\s+.*\$",
    r">\s*/etc/",
    r"rm\s+.*--no-preserve-root",
]

BLOCKED_COMMANDS: Set[str] = {
    "reboot",
    "shutdown",
    "halt",
    "poweroff",
    "init",
    "mkfs",
    "fdisk",
    "parted",
    "mount",
    "umount",
    "iptables",
    "systemctl",
    "service",
}


class ExecTool(BaseTool):
    def __init__(self, enable_sandbox: bool = True):
        super().__init__("exec_tool")
        self.enable_sandbox = enable_sandbox
        self._schema = ToolSchema(
            name="exec_tool",
            description="Execute shell commands with optional timeout and working directory",
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="Shell command to execute (string or list of args)",
                    required=True,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout in seconds",
                    required=False,
                    default=30,
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="Working directory for command execution",
                    required=False,
                ),
                ToolParameter(
                    name="env",
                    type="object",
                    description="Environment variables to set",
                    required=False,
                ),
            ],
        )

    def _normalize_command(self, command: Any) -> List[str]:
        if isinstance(command, list):
            return [str(c) for c in command]
        if isinstance(command, str):
            return shlex.split(command)
        raise ValueError("command must be str or list[str]")

    def _is_dangerous(self, command_str: str) -> Optional[str]:
        """检查命令是否包含危险操作，返回匹配的危险模式或 None"""
        if not self.enable_sandbox:
            return None

        cmd_lower = command_str.lower()

        first_word = cmd_lower.split()[0] if cmd_lower.split() else ""
        if first_word in BLOCKED_COMMANDS:
            return f"Blocked command: {first_word}"

        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command_str, re.IGNORECASE):
                return f"Dangerous pattern detected: {pattern}"

        return None

    def run(self, **params) -> ToolResult:
        cmd = params.get("command")
        timeout = params.get("timeout", 30)
        cwd = params.get("cwd")
        env = params.get("env")

        if not cmd:
            return ToolResult(success=False, error="Missing 'command' parameter")

        cmd_str = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
        danger_reason = self._is_dangerous(cmd_str)
        if danger_reason:
            return ToolResult(
                success=False,
                error=f"Command blocked by security sandbox: {danger_reason}",
            )

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
