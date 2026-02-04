from typing import Callable, Dict, Any, List, Optional
from .base_tool import ToolResult, ToolSchema, ToolParameter, BaseTool
from .file_tool import FileTool
from .exec_tool import ExecTool
from .git_tool import GitTool
from .env_tool import EnvTool


class ToolManager:
    def __init__(self, enable_sandbox: bool = True):
        self.tools: Dict[str, Callable[..., ToolResult]] = {}
        self._schemas: Dict[str, ToolSchema] = {}
        self._tool_instances: Dict[str, BaseTool] = {}

        file_tool = FileTool()
        exec_tool = ExecTool(enable_sandbox=enable_sandbox)
        git_tool = GitTool()
        env_tool = EnvTool()

        self._tool_instances["file_tool"] = file_tool
        self._tool_instances["exec_tool"] = exec_tool
        self._tool_instances["git_tool"] = git_tool
        self._tool_instances["env_tool"] = env_tool

        self._register_with_schema(
            "read_file",
            lambda **p: file_tool.run(action="read", **p),
            ToolSchema(
                name="read_file",
                description="Read content from a file",
                parameters=[
                    ToolParameter(
                        name="path",
                        type="string",
                        description="Path to the file to read",
                        required=True,
                    )
                ],
            ),
        )
        self._register_with_schema(
            "write_file",
            lambda **p: file_tool.run(action="write", **p),
            ToolSchema(
                name="write_file",
                description="Write content to a file (creates backup if file exists)",
                parameters=[
                    ToolParameter(
                        name="path",
                        type="string",
                        description="Path to the file to write",
                        required=True,
                    ),
                    ToolParameter(
                        name="content",
                        type="string",
                        description="Content to write to the file",
                        required=True,
                    ),
                ],
            ),
        )

        self._register_with_schema(
            "execute_shell",
            lambda **p: exec_tool.run(**p),
            ToolSchema(
                name="execute_shell",
                description="Execute a shell command with optional timeout and working directory",
                parameters=[
                    ToolParameter(
                        name="command",
                        type="string",
                        description="Shell command to execute",
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
                        description="Working directory",
                        required=False,
                    ),
                ],
            ),
        )

        self._register_with_schema(
            "git",
            lambda **p: git_tool.run(**p),
            ToolSchema(
                name="git",
                description="Execute git commands",
                parameters=[
                    ToolParameter(
                        name="cmd",
                        type="string",
                        description="Git command (e.g., 'git status', 'git log')",
                        required=True,
                    ),
                    ToolParameter(
                        name="cwd",
                        type="string",
                        description="Repository directory",
                        required=False,
                    ),
                ],
            ),
        )
        self._register_with_schema(
            "git_status",
            lambda **p: git_tool.status(**p),
            ToolSchema(
                name="git_status",
                description="Get git repository status",
                parameters=[
                    ToolParameter(
                        name="cwd",
                        type="string",
                        description="Repository directory",
                        required=False,
                    )
                ],
            ),
        )
        self._register_with_schema(
            "git_branch",
            lambda **p: git_tool.branch(**p),
            ToolSchema(
                name="git_branch",
                description="Create and checkout a new git branch",
                parameters=[
                    ToolParameter(
                        name="name",
                        type="string",
                        description="Name of the new branch",
                        required=True,
                    ),
                    ToolParameter(
                        name="cwd",
                        type="string",
                        description="Repository directory",
                        required=False,
                    ),
                ],
            ),
        )
        self._register_with_schema(
            "git_commit",
            lambda **p: git_tool.commit(**p),
            ToolSchema(
                name="git_commit",
                description="Stage all changes and create a commit",
                parameters=[
                    ToolParameter(
                        name="message",
                        type="string",
                        description="Commit message",
                        required=True,
                    ),
                    ToolParameter(
                        name="cwd",
                        type="string",
                        description="Repository directory",
                        required=False,
                    ),
                ],
            ),
        )

        self._register_with_schema(
            "env", lambda **p: env_tool.run(**p), env_tool.schema
        )
        self._register_with_schema(
            "check_deps",
            lambda **p: env_tool.run(action="check_deps", **p),
            ToolSchema(
                name="check_deps",
                description="List installed Python packages",
                parameters=[],
            ),
        )
        self._register_with_schema(
            "list_env",
            lambda **p: env_tool.run(action="list_env", **p),
            ToolSchema(
                name="list_env",
                description="Get Python environment information",
                parameters=[],
            ),
        )

        self._register_with_schema(
            "recover_from_error",
            self._handle_recover_from_error,
            ToolSchema(
                name="recover_from_error",
                description="Called when the agent encounters a recoverable error and needs to retry or adjust approach",
                parameters=[
                    ToolParameter(
                        name="error",
                        type="string",
                        description="Description of the error encountered",
                        required=True,
                    ),
                    ToolParameter(
                        name="retry_strategy",
                        type="string",
                        description="Strategy for recovery",
                        required=False,
                    ),
                ],
            ),
        )
        self._register_with_schema(
            "system_error",
            self._handle_system_error,
            ToolSchema(
                name="system_error",
                description="Called when a system-level error occurs",
                parameters=[
                    ToolParameter(
                        name="message",
                        type="string",
                        description="Error message",
                        required=True,
                    )
                ],
            ),
        )
        self._register_with_schema(
            "finish",
            self._handle_finish,
            ToolSchema(
                name="finish",
                description="Signal that the task is complete",
                parameters=[
                    ToolParameter(
                        name="summary",
                        type="string",
                        description="Summary of what was accomplished",
                        required=False,
                    )
                ],
            ),
        )

    def _register_with_schema(
        self, name: str, func: Callable[..., ToolResult], schema: ToolSchema
    ):
        self.tools[name] = func
        self._schemas[name] = schema

    def register_tool(
        self,
        name: str,
        func: Callable[..., ToolResult],
        schema: Optional[ToolSchema] = None,
    ):
        self.tools[name] = func
        if schema:
            self._schemas[name] = schema

    def _handle_recover_from_error(self, **params) -> ToolResult:
        error = params.get("error", "Unknown error")
        strategy = params.get("retry_strategy", "")
        return ToolResult(
            success=True,
            data=f"Recovery initiated for error: {error}. Strategy: {strategy or 'default retry'}",
        )

    def _handle_system_error(self, **params) -> ToolResult:
        message = params.get("message", "Unknown system error")
        return ToolResult(success=False, error=f"System error: {message}")

    def _handle_finish(self, **params) -> ToolResult:
        summary = params.get("summary", "Task completed")
        return ToolResult(success=True, data=summary)

    def call(self, name: str, params: Dict[str, Any]) -> Any:
        if name not in self.tools:
            available = ", ".join(sorted(self.tools.keys()))
            return f"Error: Tool '{name}' not found. Available tools: {available}"

        try:
            result: ToolResult = self.tools[name](**(params or {}))
        except TypeError as e:
            return f"Error: Invalid parameters for tool '{name}': {e}"
        except Exception as e:
            return f"Error: Tool '{name}' execution failed: {e}"

        if isinstance(result, ToolResult):
            if result.success:
                if isinstance(result.data, str):
                    return result.data
                return str(result.data)
            else:
                return f"Error: {result.error}"

        return result

    def get_tool(self, name: str) -> Optional[Callable[..., ToolResult]]:
        return self.tools.get(name)

    def get_schema(self, name: str) -> Optional[ToolSchema]:
        return self._schemas.get(name)

    def get_all_schemas(self) -> Dict[str, ToolSchema]:
        return self._schemas.copy()

    def get_tools_prompt(self) -> str:
        lines = []
        for name in sorted(self._schemas.keys()):
            schema = self._schemas[name]
            lines.append(schema.to_prompt_string())
        return "\n\n".join(lines)

    def get_tools_json_schema(self) -> List[Dict[str, Any]]:
        return [schema.to_json_schema() for schema in self._schemas.values()]
