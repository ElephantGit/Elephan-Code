from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod


@dataclass
class ToolResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass
class ToolParameter:
    """工具参数描述"""

    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None


@dataclass
class ToolSchema:
    """工具的完整 Schema 描述"""

    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)

    def to_json_schema(self) -> Dict[str, Any]:
        """转换为 JSON Schema 格式"""
        properties: Dict[str, Any] = {}
        required: List[str] = []

        for param in self.parameters:
            prop: Dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def to_prompt_string(self) -> str:
        """转换为可读的 prompt 字符串"""
        params_str = []
        for p in self.parameters:
            req = "(required)" if p.required else "(optional)"
            enum_str = f", one of: {p.enum}" if p.enum else ""
            default_str = f", default: {p.default}" if p.default is not None else ""
            params_str.append(
                f"    - {p.name} ({p.type}, {req}): {p.description}{enum_str}{default_str}"
            )

        params_section = "\n".join(params_str) if params_str else "    (no parameters)"
        return f"- {self.name}: {self.description}\n  Parameters:\n{params_section}"


class BaseTool(ABC):
    """抽象工具基类。具体工具应继承并实现 `run` 方法和 `schema` 属性。"""

    name: str
    _schema: Optional[ToolSchema] = None

    def __init__(self, name: str):
        self.name = name

    @property
    def schema(self) -> ToolSchema:
        """返回工具的 Schema，子类应覆盖此属性或在初始化时设置 _schema"""
        if self._schema:
            return self._schema
        return ToolSchema(
            name=self.name, description=f"Tool: {self.name}", parameters=[]
        )

    @abstractmethod
    def run(self, **params) -> ToolResult:
        raise NotImplementedError()
