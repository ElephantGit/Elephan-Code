"""Agent 的自动模式 - 智能决定是否需要预规划"""

from typing import Any, Dict, Optional
import logging
from elephan_code.agent.agent_modes import AgentMode
from elephan_code.agent.plan.plan_decider import PlanDecider, PlanDecision
from elephan_code.agent.plan.plan_mode import PlanGenerator, Plan
from elephan_code.agent.build_mode import BuildMode
from elephan_code.agent.standard_mode import StandardMode

logger = logging.getLogger(__name__)


class AutoMode(AgentMode):
    """自动执行模式

    智能判断任务复杂度：
    - 简单任务：StandardMode 直接执行
    - 复杂任务：生成计划后用 BuildMode 按步骤执行
    """

    def __init__(self, agent):
        super().__init__(agent, "auto")
        self.decider = PlanDecider(agent.llm)
        self.plan_generator = PlanGenerator(agent.llm, agent.tools)
        self.build_mode = BuildMode(agent)
        self.standard_mode = StandardMode(agent)

        self.last_decision: Optional[PlanDecision] = None
        self.last_plan: Optional[Plan] = None

    def register_callback(self, event_name: str, callback) -> None:
        super().register_callback(event_name, callback)
        self.build_mode.register_callback(event_name, callback)
        self.standard_mode.register_callback(event_name, callback)

    async def run(self, task: str, max_steps: int = 10) -> Dict[str, Any]:
        """执行任务，自动选择是否使用计划"""
        self.is_running = True

        try:
            self.trigger_callback("on_status_update", "Analyzing task...")
            decision = await self.decider.should_plan(task)
            self.last_decision = decision
            self.trigger_callback("on_decision_made", decision)

            if decision.needs_planning:
                self.trigger_callback("on_status_update", "Generating plan...")
                plan = await self.plan_generator.generate(task)
                self.last_plan = plan

                self.trigger_callback(
                    "on_status_update", f"Executing plan ({len(plan)} steps)..."
                )
                result = await self.build_mode.run(task, plan, max_steps=max_steps)
            else:
                self.trigger_callback("on_status_update", "Executing directly...")
                self.last_plan = None
                result = await self.standard_mode.run(task, max_steps=max_steps)

            result["decision"] = decision.to_dict()
            result["used_planning"] = decision.needs_planning
            if self.last_plan:
                result["plan"] = self.last_plan.to_dict()

            self.is_running = False
            return result

        except Exception as e:
            logger.error(f"AutoMode execution failed: {e}", exc_info=True)
            self.is_running = False
            self.trigger_callback("on_execution_error", str(e))
            return {
                "success": False,
                "error": str(e),
                "decision": self.last_decision.to_dict()
                if self.last_decision
                else None,
            }

    def stop(self) -> None:
        super().stop()
        self.build_mode.stop()
        self.standard_mode.stop()
