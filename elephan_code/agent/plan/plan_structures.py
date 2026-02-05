"""Plan Mode 数据结构定义"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


class StepStatus(Enum):
    """步骤执行状态"""
    NOT_STARTED = "not-started"      # ☐
    IN_PROGRESS = "in-progress"      # ⦿
    COMPLETED = "completed"          # ✓
    FAILED = "failed"                # ✗
    SKIPPED = "skipped"              # ⊘
    BLOCKED = "blocked"              # ◆ 依赖未满足


@dataclass
class StepProgress:
    """步骤进度跟踪"""
    step_id: int
    description: str = ""
    status: StepStatus = StepStatus.NOT_STARTED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    observation: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # 子任务追踪（如一个步骤包含多个工具调用）
    subtasks: Dict[str, bool] = field(default_factory=dict)
    subtask_count: int = 0
    subtask_completed: int = 0
    
    def progress_percentage(self) -> float:
        """计算该步骤的完成百分比"""
        if self.subtask_count == 0:
            return 100.0 if self.status == StepStatus.COMPLETED else 0.0
        return (self.subtask_completed / self.subtask_count) * 100
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "step_id": self.step_id,
            "description": self.description,
            "status": self.status.value,
            "progress": self.progress_percentage(),
            "duration": self.duration_seconds,
            "retry_count": self.retry_count,
        }


@dataclass
class PlanProgress:
    """整体计划进度"""
    plan_id: str
    task: str
    total_steps: int
    steps_progress: Dict[int, StepProgress] = field(default_factory=dict)
    overall_status: StepStatus = StepStatus.NOT_STARTED
    
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    def get_overall_progress(self) -> float:
        """计算整体完成度（0-100%）"""
        if not self.steps_progress:
            return 0.0
        
        completed = sum(
            1 for sp in self.steps_progress.values()
            if sp.status == StepStatus.COMPLETED
        )
        return (completed / self.total_steps) * 100
    
    def get_blocked_steps(self) -> List[int]:
        """获取被阻塞的步骤"""
        return [
            step_id for step_id, sp in self.steps_progress.items()
            if sp.status == StepStatus.BLOCKED
        ]
    
    def get_failed_steps(self) -> List[int]:
        """获取失败的步骤"""
        return [
            step_id for step_id, sp in self.steps_progress.items()
            if sp.status == StepStatus.FAILED
        ]
    
    def get_in_progress_step(self) -> Optional[int]:
        """获取当前进行中的步骤"""
        for step_id, sp in self.steps_progress.items():
            if sp.status == StepStatus.IN_PROGRESS:
                return step_id
        return None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task": self.task,
            "overall_progress": self.get_overall_progress(),
            "total_steps": self.total_steps,
            "completed_steps": sum(
                1 for sp in self.steps_progress.values()
                if sp.status == StepStatus.COMPLETED
            ),
            "failed_steps": len(self.get_failed_steps()),
            "blocked_steps": len(self.get_blocked_steps()),
        }
