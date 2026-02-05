"""Agent 的计划生成模式 - 仅负责生成执行计划"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
import json
import logging

if TYPE_CHECKING:
    from elephan_code.agent.plan_todo import PlanTodoManager

logger = logging.getLogger(__name__)


@dataclass
class Step:
    """Plan Mode 中的步骤定义"""

    step_id: int
    description: str
    tools: List[str] = field(default_factory=list)
    dependencies: List[int] = field(default_factory=list)
    expected_output: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "step_id": self.step_id,
            "description": self.description,
            "tools": self.tools,
            "dependencies": self.dependencies,
            "expected_output": self.expected_output,
        }


@dataclass
class Plan:
    """执行计划"""

    task: str
    steps: List[Step] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task": self.task,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
        }

    def get_step_descriptions(self) -> List[str]:
        """获取所有步骤的描述列表"""
        return [step.description for step in self.steps]

    def __len__(self) -> int:
        return len(self.steps)


class PlanGenerator:
    """计划生成器 - 使用 LLM 生成任务执行计划

    职责单一：只负责生成计划，不负责执行
    """

    # 计划生成 prompt 模板
    PLAN_PROMPT = """你是一个规划专家。请为以下任务制定详细的执行计划。

任务: {task}

可用工具: {tools}

请以以下 JSON 格式返回计划：
{{
    "task": "任务描述",
    "description": "计划概述",
    "steps": [
        {{
            "step_id": 1,
            "description": "第一步的描述",
            "tools": ["tool1", "tool2"],
            "dependencies": [],
            "expected_output": "预期输出"
        }},
        ...
    ]
}}

要求:
1. 每个步骤应该清晰且可执行
2. 步骤顺序应该逻辑清晰
3. 指定每个步骤需要的工具（从可用工具中选择）
4. 指定步骤间的依赖关系（用 step_id 列表表示）
5. 共 3-7 个步骤为佳

返回 JSON 对象，不包含其他文本。"""

    def __init__(self, llm, tool_manager=None):
        """初始化计划生成器

        Args:
            llm: LLM 接口实例
            tool_manager: 可选的工具管理器，用于获取可用工具列表
        """
        self.llm = llm
        self.tool_manager = tool_manager

    def _get_available_tools(self) -> str:
        """获取可用工具列表"""
        if self.tool_manager and hasattr(self.tool_manager, "get_tool_names"):
            tools = self.tool_manager.get_tool_names()
            return (
                ", ".join(tools)
                if tools
                else "read_file, write_file, execute_shell, git"
            )
        return "read_file, write_file, execute_shell, git"

    async def generate(self, task: str) -> Plan:
        """使用 LLM 生成任务执行计划

        Args:
            task: 要规划的任务

        Returns:
            生成的执行计划
        """
        logger.info(f"Generating plan for task: {task[:50]}...")

        try:
            tools = self._get_available_tools()
            prompt = self.PLAN_PROMPT.format(task=task, tools=tools)

            response = self.llm.plan_ask(
                [
                    {
                        "role": "system",
                        "content": "You are a planning expert. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ]
            )

            # 解析响应
            if hasattr(response, "model_dump_json"):
                response_text = response.model_dump_json()
            elif hasattr(response, "thought"):
                response_text = str(response.thought)
            else:
                response_text = str(response)

            plan = self._parse_plan(response_text, task)
            logger.info(f"Generated plan with {len(plan)} steps")
            return plan

        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            # 返回简单的单步计划作为后备
            return self._create_fallback_plan(task)

    def generate_sync(self, task: str) -> Plan:
        """同步版本的计划生成

        Args:
            task: 要规划的任务

        Returns:
            生成的执行计划
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.generate(task))
                    return future.result()
            else:
                return loop.run_until_complete(self.generate(task))
        except RuntimeError:
            return asyncio.run(self.generate(task))

    def _parse_plan(self, response_text: str, original_task: str) -> Plan:
        """解析 LLM 的计划响应

        Args:
            response_text: LLM 响应文本
            original_task: 原始任务描述

        Returns:
            Plan 对象
        """
        try:
            text = response_text.strip()

            # 提取 JSON
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()

            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                text = text[json_start:json_end]

            plan_dict = json.loads(text)

            steps = []
            for step_dict in plan_dict.get("steps", []):
                step = Step(
                    step_id=step_dict.get("step_id", len(steps) + 1),
                    description=step_dict.get("description", ""),
                    tools=step_dict.get("tools", []),
                    dependencies=step_dict.get("dependencies", []),
                    expected_output=step_dict.get("expected_output", ""),
                )
                steps.append(step)

            return Plan(
                task=plan_dict.get("task", original_task),
                steps=steps,
                description=plan_dict.get("description", ""),
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse plan JSON: {e}")
            return self._create_fallback_plan(original_task)

    def _create_fallback_plan(self, task: str) -> Plan:
        """创建后备单步计划

        Args:
            task: 任务描述

        Returns:
            简单的单步计划
        """
        return Plan(
            task=task,
            steps=[
                Step(
                    step_id=1,
                    description=task,
                    tools=[],
                    dependencies=[],
                    expected_output="Task completed",
                )
            ],
            description="Fallback single-step plan",
        )

