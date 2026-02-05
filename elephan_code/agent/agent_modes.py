"""Agent 执行模式的抽象基类和实现"""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)


class AgentMode(ABC):
    """Agent 执行模式的抽象基类
    
    提供统一的接口来支持不同的 Agent 执行模式（标准模式、计划模式、构建模式等）
    """
    
    def __init__(self, agent, mode_name: str):
        """初始化 Agent 模式
        
        Args:
            agent: Agent 实例
            mode_name: 模式名称
        """
        self.agent = agent
        self.mode_name = mode_name
        self.is_running = False
        self.callbacks: Dict[str, Callable] = {}
        
        logger.info(f"Agent mode '{mode_name}' initialized")
    
    @abstractmethod
    async def run(self, task: str, max_steps: int = 10) -> Dict[str, Any]:
        """执行任务
        
        Args:
            task: 要执行的任务
            max_steps: 最大步数
            
        Returns:
            执行结果字典
        """
        pass
    
    def register_callback(self, event_name: str, callback: Callable) -> None:
        """注册事件回调
        
        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        self.callbacks[event_name] = callback
        logger.debug(f"Callback '{event_name}' registered for mode '{self.mode_name}'")
    
    def trigger_callback(self, event_name: str, *args, **kwargs) -> None:
        """触发事件回调
        
        Args:
            event_name: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数
        """
        if event_name in self.callbacks:
            try:
                self.callbacks[event_name](*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in callback '{event_name}': {e}")
    
    def stop(self) -> None:
        """停止执行"""
        self.is_running = False
        logger.info(f"Agent mode '{self.mode_name}' stopped")
