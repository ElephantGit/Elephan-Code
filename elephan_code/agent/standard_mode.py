"""Agent 的标准执行模式 - 逐步执行，可选预规划"""

from typing import Any, Dict, Optional, List, TYPE_CHECKING
import logging
from elephan_code.agent.agent_modes import AgentMode

if TYPE_CHECKING:
    from elephan_code.agent.plan.plan_mode import Plan

logger = logging.getLogger(__name__)


class StandardMode(AgentMode):
    """标准执行模式

    逐步思考、调用工具和观察结果。
    支持可选的预规划：当传入 Plan 对象时，会按计划步骤引导执行。
    """

    def __init__(self, agent):
        """初始化标准模式

        Args:
            agent: Agent 实例
        """
        super().__init__(agent, "standard")
        self.current_plan: Optional["Plan"] = None
        self.current_step_index: int = 0

    def set_plan(self, plan: Optional["Plan"]) -> None:
        """设置执行计划

        Args:
            plan: Plan 对象，设为 None 则清除计划
        """
        self.current_plan = plan
        self.current_step_index = 0
        if plan:
            logger.info(f"Plan set with {len(plan)} steps")

    def _get_current_step_context(self) -> str:
        """获取当前步骤的上下文提示"""
        if not self.current_plan or self.current_step_index >= len(
            self.current_plan.steps
        ):
            return ""

        step = self.current_plan.steps[self.current_step_index]
        remaining = len(self.current_plan.steps) - self.current_step_index

        context = f"""
[执行计划指导]
当前步骤 ({self.current_step_index + 1}/{len(self.current_plan.steps)}): {step.description}
预期使用工具: {", ".join(step.tools) if step.tools else "自动选择"}
预期输出: {step.expected_output or "完成步骤目标"}
剩余步骤: {remaining - 1}

请专注于完成当前步骤。完成后我会告诉你下一步。
"""
        return context

    def _advance_step(self) -> bool:
        """推进到下一个步骤

        Returns:
            是否还有更多步骤
        """
        if not self.current_plan:
            return False

        self.current_step_index += 1
        if self.current_step_index >= len(self.current_plan.steps):
            logger.info("All plan steps completed")
            return False

        logger.info(f"Advanced to step {self.current_step_index + 1}")
        return True

    async def run(
        self, task: str, max_steps: int = 10, plan: Optional["Plan"] = None
    ) -> Dict[str, Any]:
        """以标准模式执行任务

        Args:
            task: 要执行的任务
            max_steps: 最大步数限制
            plan: 可选的执行计划

        Returns:
            执行结果字典
        """
        self.is_running = True
        messages = []

        # 设置计划（如果提供）
        if plan:
            self.set_plan(plan)
            logger.info(f"Standard mode: Executing with plan ({len(plan)} steps)")
        else:
            logger.info("Standard mode: Executing without plan")

        self.trigger_callback("on_execution_start", task)

        try:
            # 构建初始任务消息
            if self.current_plan:
                # 有计划时，添加计划上下文
                plan_context = self._build_plan_context()
                full_task = f"{task}\n\n{plan_context}"
            else:
                full_task = task

            self.agent.memory.append({"role": "user", "content": full_task})

            if self.agent.trajectory:
                self.agent.trajectory.start(task)

            steps_taken = 0
            plan_steps_completed = 0

            for _ in range(max_steps):
                if not self.is_running:
                    break

                # 如果有计划，检查当前步骤并添加引导
                if self.current_plan and self.current_step_index < len(
                    self.current_plan.steps
                ):
                    step_context = self._get_current_step_context()
                    if step_context and steps_taken > 0:
                        # 在后续步骤添加引导上下文
                        self.agent.memory.append(
                            {"role": "user", "content": step_context}
                        )

                # 执行一步
                if not self.agent.step():
                    break

                steps_taken += 1

                # 如果有计划，检查是否完成当前步骤
                if self.current_plan:
                    # 简单启发式：每执行一步就推进计划步骤
                    # 更复杂的实现可以分析 observation 来判断
                    if self._should_advance_step():
                        if not self._advance_step():
                            # 所有计划步骤完成
                            plan_steps_completed = len(self.current_plan.steps)
                            break
                        plan_steps_completed = self.current_step_index

            if self.agent.trajectory:
                self.agent.trajectory.end(status="completed")

            self.is_running = False

            result = {
                "task": task,
                "steps_taken": steps_taken,
                "had_plan": self.current_plan is not None,
            }

            if self.current_plan:
                result["plan_steps_completed"] = plan_steps_completed
                result["plan_total_steps"] = len(self.current_plan.steps)

            self.trigger_callback("on_execution_end", result)

            return {
                "success": True,
                "result": result,
                "steps_taken": steps_taken,
                "messages": messages,
            }

        except Exception as e:
            logger.error(f"Standard mode execution failed: {e}", exc_info=True)
            self.is_running = False
            self.trigger_callback("on_execution_error", str(e))

            return {"success": False, "error": str(e), "messages": messages}
        finally:
            # 清理计划状态
            self.current_plan = None
            self.current_step_index = 0

    def _build_plan_context(self) -> str:
        """构建完整的计划上下文"""
        if not self.current_plan:
            return ""

        lines = [
            "[执行计划]",
            f"计划描述: {self.current_plan.description}",
            "",
            "步骤列表:",
        ]

        for i, step in enumerate(self.current_plan.steps):
            prefix = "→ " if i == self.current_step_index else "  "
            lines.append(f"{prefix}{i + 1}. {step.description}")
            if step.tools:
                lines.append(f"     工具: {', '.join(step.tools)}")

        lines.append("")
        lines.append(f"从步骤 1 开始执行。")

        return "\n".join(lines)

    def _should_advance_step(self) -> bool:
        """判断是否应该推进到下一步

        简单实现：默认每个 agent step 对应一个计划 step
        可以扩展为分析 observation 内容来智能判断
        """
        # 获取最后的 observation
        if len(self.agent.memory) < 2:
            return False

        last_message = self.agent.memory[-1]
        if last_message.get("role") != "user":
            return False

        content = last_message.get("content", "")

        # 如果 observation 包含成功信号，推进步骤
        success_signals = ["完成", "成功", "done", "success", "completed", "✓"]
        return any(signal in content.lower() for signal in success_signals)
