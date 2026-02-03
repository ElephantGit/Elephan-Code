from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod


@dataclass
class ToolResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    meta: Dict[str, Any] = None


class BaseTool(ABC):
    """抽象工具基类。具体工具应继承并实现 `run` 方法。"""

    name: str

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, **params) -> ToolResult:
        raise NotImplementedError()
