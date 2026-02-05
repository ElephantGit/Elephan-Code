"""Agent 的构建模式 - 按计划步骤逐步执行"""

from typing import Any, Dict, Optional, Callable, TYPE_CHECKING
import logging
from elephan_code.agent.plan.plan_structures import StepStatus
from elephan_code.agent.plan.plan_todo import PlanTodoManager

if TYPE_CHECKING:
    from elephan_code.agent.plan.plan_mode import Plan, Step

logger = logging.getLogger(__name__)


class BuildMode:
    """构建执行模式 - 按计划步骤执行任务

    与 StandardMode 的区别：
    - 明确按 Plan 的每个 Step 执行
    - 每个 Step 可能需要多次 agent.step() 调用
    - 触发完整的步骤生命周期回调
    """

    def __init__(self, agent):
        self.agent = agent
        self.mode_name = "build"
        self.is_running = False
        self.callbacks: Dict[str, Callable] = {}
        self.plan_manager: Optional[PlanTodoManager] = None
        self.max_iterations_per_step: int = 5

    def register_callback(self, event_name: str, callback: Callable) -> None:
        self.callbacks[event_name] = callback

    def trigger_callback(self, event_name: str, *args, **kwargs) -> None:
        if event_name in self.callbacks:
            try:
                self.callbacks[event_name](*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error '{event_name}': {e}")

    def stop(self) -> None:
        self.is_running = False

    async def run(self, task: str, plan: "Plan", max_steps: int = 10) -> Dict[str, Any]:
        """按计划执行任务"""
        self.is_running = True
        total_agent_steps = 0

        self.plan_manager = PlanTodoManager(plan, plan_id=task.replace(" ", "_")[:20])
        self.trigger_callback("on_plan_created", plan, self.plan_manager)
        self.trigger_callback("on_execution_start", task)

        try:
            for step_index, step in enumerate(plan.steps):
                if not self.is_running or total_agent_steps >= max_steps:
                    break

                if not self.plan_manager.check_dependencies(step.step_id):
                    self.plan_manager.block_step(step.step_id)
                    self.trigger_callback("on_step_blocked", step)
                    continue

                steps_used = await self._execute_step(
                    step, step_index, len(plan.steps), max_steps - total_agent_steps
                )
                total_agent_steps += steps_used

            self.is_running = False
            progress = self.plan_manager.progress.get_overall_progress()

            result = {
                "success": progress >= 100.0,
                "progress": progress,
                "total_steps": total_agent_steps,
                "plan_steps_completed": sum(
                    1
                    for sp in self.plan_manager.progress.steps_progress.values()
                    if sp.status == StepStatus.COMPLETED
                ),
                "plan_total_steps": len(plan.steps),
                "summary": self.plan_manager.get_todo_summary(),
            }

            self.trigger_callback("on_execution_end", result)
            return result

        except Exception as e:
            logger.error(f"BuildMode failed: {e}", exc_info=True)
            self.is_running = False
            self.trigger_callback("on_execution_error", str(e))
            return {"success": False, "error": str(e)}

    async def _execute_step(
        self, step: "Step", step_index: int, total_steps: int, remaining: int
    ) -> int:
        """执行单个计划步骤"""
        self.plan_manager.start_step(step.step_id)
        self.trigger_callback("on_step_start", step)

        prompt = f"[Step {step_index + 1}/{total_steps}] {step.description}"
        if step.expected_output:
            prompt += f"\nExpected: {step.expected_output}"
        if step.tools:
            prompt += f"\nTools: {', '.join(step.tools)}"
        prompt += "\nCall 'finish' when done with this step."

        self.agent.memory.append({"role": "user", "content": prompt})

        steps_used = 0
        max_for_step = min(self.max_iterations_per_step, remaining)

        for iteration in range(max_for_step):
            if not self.is_running:
                break

            continue_running = self.agent.step()
            steps_used += 1

            if not continue_running or self._is_step_done():
                break

        observation = self._get_last_observation()
        self.plan_manager.complete_step(step.step_id, observation)
        self.trigger_callback("on_step_completed", step, observation)

        return steps_used

    def _is_step_done(self) -> bool:
        if not self.agent.memory:
            return False
        last = self.agent.memory[-1].get("content", "")
        signals = ["finish", "done", "completed", "完成"]
        return any(s in last.lower() for s in signals)

    def _get_last_observation(self) -> str:
        for msg in reversed(self.agent.memory):
            content = msg.get("content", "")
            if "Observation:" in content:
                return content[:300]
        return ""
