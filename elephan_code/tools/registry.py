from typing import Callable, Dict, Any
from .base_tool import ToolResult
from .file_tool import FileTool
from .exec_tool import ExecTool
from .git_tool import GitTool
from .env_tool import EnvTool


class ToolManager:
    """兼容旧的 ToolManager 接口，同时基于可扩展的工具实现。"""

    def __init__(self):
        self.tools: Dict[str, Callable[..., ToolResult]] = {}

        # 注册基础工具（兼容旧名称）
        file_tool = FileTool()
        exec_tool = ExecTool()
        git_tool = GitTool()
        env_tool = EnvTool()

        # register callable wrappers that accept kwargs
        self.register_tool("read_file", lambda **p: file_tool.run(action="read", **p))
        self.register_tool("write_file", lambda **p: file_tool.run(action="write", **p))
        # 保留旧拼写以兼容现有代码
        self.register_tool("excute_shell", lambda **p: exec_tool.run(**p))
        # 添加正确拼写别名
        self.register_tool("execute_shell", lambda **p: exec_tool.run(**p))
        # git and env tools
        self.register_tool("git", lambda **p: git_tool.run(**p))
        self.register_tool("git_status", lambda **p: git_tool.status(**p))
        self.register_tool("git_branch", lambda **p: git_tool.branch(**p))
        self.register_tool("git_commit", lambda **p: git_tool.commit(**p))

        self.register_tool("env", lambda **p: env_tool.run(**p))
        self.register_tool("check_deps", lambda **p: env_tool.run(action="check_deps", **p))
        self.register_tool("list_env", lambda **p: env_tool.run(action="list_env", **p))

    def register_tool(self, name: str, func: Callable[..., ToolResult]):
        self.tools[name] = func

    def call(self, name: str, params: Dict[str, Any]):
        if name not in self.tools:
            return f"Error Tool {name} not found."

        try:
            result: ToolResult = self.tools[name](**(params or {}))
        except TypeError:
            # fallback: pass params directly
            result = self.tools[name](**(params or {}))

        # 兼容旧接口：如果工具返回 ToolResult，则把常见情况转换为字符串。
        if isinstance(result, ToolResult):
            if result.success:
                # 如果 data 是字符串，直接返回；否则返回简单序列化表示
                if isinstance(result.data, str):
                    return result.data
                return str(result.data)
            else:
                return f"Error: {result.error}"

        # 如果工具返回原始字符串或其他类型，直接返回
        return result

    def get_tool(self, name: str):
        return self.tools.get(name)
