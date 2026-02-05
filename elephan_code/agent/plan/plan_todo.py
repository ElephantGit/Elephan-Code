"""Plan Mode 的 Todo 管理器"""

from datetime import datetime
from typing import Dict, List, Optional
from elephan_code.agent.plan.plan_structures import StepProgress, PlanProgress, StepStatus
from elephan_code.utils.logging import get_logger

logger = get_logger("elephan.plan_todo")


class PlanTodoManager:
    """管理和追踪计划的 todo 状态"""
    
    def __init__(self, plan, plan_id: Optional[str] = None):
        """
        初始化 todo 管理器
        
        Args:
            plan: Plan 对象，包含 task 和 steps
            plan_id: 可选的计划ID，用于标识计划
        """
        self.plan = plan
        self.progress = PlanProgress(
            plan_id=plan_id or str(id(plan)),
            task=plan.task,
            total_steps=len(plan.steps)
        )
        self._initialize_steps()
        logger.info(f"PlanTodoManager initialized for task: {plan.task}")
    
    def _initialize_steps(self):
        """初始化所有步骤的进度"""
        for step in self.plan.steps:
            self.progress.steps_progress[step.step_id] = StepProgress(
                step_id=step.step_id,
                description=step.description,
                subtask_count=len(step.tools) if hasattr(step, 'tools') else 0
            )
    
    def start_step(self, step_id: int) -> bool:
        """
        标记步骤开始
        
        Args:
            step_id: 步骤 ID
            
        Returns:
            是否成功启动步骤
        """
        if step_id not in self.progress.steps_progress:
            logger.error(f"Step {step_id} not found")
            return False
        
        sp = self.progress.steps_progress[step_id]
        sp.status = StepStatus.IN_PROGRESS
        sp.started_at = datetime.now()
        logger.info(f"Step {step_id} started")
        return True
    
    def update_subtask(self, step_id: int, subtask_name: str, completed: bool) -> bool:
        """
        更新步骤内的子任务
        
        Args:
            step_id: 步骤 ID
            subtask_name: 子任务名称
            completed: 是否完成
            
        Returns:
            是否成功更新
        """
        if step_id not in self.progress.steps_progress:
            logger.error(f"Step {step_id} not found")
            return False
        
        sp = self.progress.steps_progress[step_id]
        sp.subtasks[subtask_name] = completed
        sp.subtask_completed = sum(1 for v in sp.subtasks.values() if v)
        logger.debug(f"Step {step_id} subtask '{subtask_name}' updated: {completed}")
        return True
    
    def complete_step(self, step_id: int, observation: str = "") -> bool:
        """
        标记步骤完成
        
        Args:
            step_id: 步骤 ID
            observation: 步骤的观察结果/输出
            
        Returns:
            是否成功完成步骤
        """
        if step_id not in self.progress.steps_progress:
            logger.error(f"Step {step_id} not found")
            return False
        
        sp = self.progress.steps_progress[step_id]
        sp.status = StepStatus.COMPLETED
        sp.completed_at = datetime.now()
        sp.observation = observation
        if sp.started_at:
            sp.duration_seconds = (sp.completed_at - sp.started_at).total_seconds()
        else:
            sp.duration_seconds = 0.0
        logger.info(f"Step {step_id} completed in {sp.duration_seconds:.2f}s")
        return True
    
    def fail_step(self, step_id: int, error_message: str = "") -> bool:
        """
        标记步骤失败
        
        Args:
            step_id: 步骤 ID
            error_message: 错误信息
            
        Returns:
            是否成功标记为失败
        """
        if step_id not in self.progress.steps_progress:
            logger.error(f"Step {step_id} not found")
            return False
        
        sp = self.progress.steps_progress[step_id]
        sp.status = StepStatus.FAILED
        sp.completed_at = datetime.now()
        sp.error_message = error_message
        sp.retry_count += 1
        logger.error(f"Step {step_id} failed: {error_message}")
        return True
    
    def skip_step(self, step_id: int, reason: str = "") -> bool:
        """
        跳过步骤
        
        Args:
            step_id: 步骤 ID
            reason: 跳过原因
            
        Returns:
            是否成功跳过步骤
        """
        if step_id not in self.progress.steps_progress:
            logger.error(f"Step {step_id} not found")
            return False
        
        sp = self.progress.steps_progress[step_id]
        sp.status = StepStatus.SKIPPED
        sp.observation = reason
        logger.info(f"Step {step_id} skipped: {reason}")
        return True
    
    def block_step(self, step_id: int, reason: str = "Dependencies not met") -> bool:
        """
        标记步骤被阻塞
        
        Args:
            step_id: 步骤 ID
            reason: 阻塞原因
            
        Returns:
            是否成功标记为阻塞
        """
        if step_id not in self.progress.steps_progress:
            logger.error(f"Step {step_id} not found")
            return False
        
        sp = self.progress.steps_progress[step_id]
        sp.status = StepStatus.BLOCKED
        sp.observation = reason
        logger.warning(f"Step {step_id} blocked: {reason}")
        return True
    
    def check_dependencies(self, step_id: int) -> bool:
        """
        检查步骤依赖是否满足
        
        Args:
            step_id: 步骤 ID
            
        Returns:
            依赖是否全部满足
        """
        if step_id not in self.progress.steps_progress:
            logger.error(f"Step {step_id} not found")
            return False
        
        step = next((s for s in self.plan.steps if s.step_id == step_id), None)
        if not step:
            return False
        
        # 检查所有依赖步骤是否已完成
        for dep_id in step.dependencies:
            dep_progress = self.progress.steps_progress.get(dep_id)
            if not dep_progress or dep_progress.status != StepStatus.COMPLETED:
                self.block_step(step_id, f"Depends on step {dep_id}")
                return False
        
        return True
    
    def get_todo_summary(self) -> str:
        """获取 todo 列表的文本摘要"""
        lines = [f"计划: {self.plan.task}"]
        lines.append(f"进度: {self.progress.get_overall_progress():.1f}%")
        lines.append("")
        
        for step in self.plan.steps:
            sp = self.progress.steps_progress[step.step_id]
            status_icon = self._get_status_icon(sp.status)
            
            if sp.subtask_count > 0:
                subtask_info = f" ({sp.subtask_completed}/{sp.subtask_count})"
            else:
                subtask_info = ""
            
            duration_info = ""
            if sp.duration_seconds:
                duration_info = f" [{sp.duration_seconds:.1f}s]"
            
            lines.append(
                f"{status_icon} [Step {step.step_id}] {step.description}"
                f"{subtask_info}{duration_info}"
            )
        
        return "\n".join(lines)
    
    @staticmethod
    def _get_status_icon(status: StepStatus) -> str:
        """获取状态图标"""
        icons = {
            StepStatus.NOT_STARTED: "☐",
            StepStatus.IN_PROGRESS: "⦿",
            StepStatus.COMPLETED: "✓",
            StepStatus.FAILED: "✗",
            StepStatus.SKIPPED: "⊘",
            StepStatus.BLOCKED: "◆",
        }
        return icons.get(status, "?")
    
    def get_progress_dict(self) -> dict:
        """获取进度的字典表示"""
        return self.progress.to_dict()
    
    def print_summary(self):
        """打印 todo 摘要到日志"""
        logger.info("\n" + self.get_todo_summary())
