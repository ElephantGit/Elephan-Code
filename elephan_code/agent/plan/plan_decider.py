"""智能计划决策器 - 使用 LLM 判断任务是否需要预规划"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """任务复杂度级别"""

    SIMPLE = "simple"  # 简单任务，直接执行
    MODERATE = "moderate"  # 中等复杂度，可选规划
    COMPLEX = "complex"  # 复杂任务，建议规划


@dataclass
class PlanDecision:
    """规划决策结果"""

    needs_planning: bool
    complexity: TaskComplexity
    reasoning: str
    suggested_steps: int = 0  # 建议的步骤数（如果需要规划）

    def to_dict(self) -> dict:
        return {
            "needs_planning": self.needs_planning,
            "complexity": self.complexity.value,
            "reasoning": self.reasoning,
            "suggested_steps": self.suggested_steps,
        }


class PlanDecider:
    """使用 LLM 判断任务是否需要预规划的决策器"""

    # 决策 prompt 模板
    DECISION_PROMPT = """你是一个任务分析专家。分析以下任务，判断是否需要预先制定执行计划。

任务: {task}

分析标准:
1. 简单任务 (SIMPLE): 单一目标，1-2 步即可完成，无需规划
   例如: "读取 README.md 文件", "查看当前目录结构", "检查 git 状态"

2. 中等复杂度 (MODERATE): 有明确目标，需要 3-5 步，可选规划
   例如: "修复这个 bug", "添加一个简单的函数", "格式化代码"

3. 复杂任务 (COMPLEX): 多个子目标，需要 5+ 步骤，涉及多文件/多工具，建议规划
   例如: "重构整个模块", "添加新功能并编写测试", "迁移数据库结构"

请以 JSON 格式返回你的分析结果:
{{
    "needs_planning": true/false,
    "complexity": "simple" | "moderate" | "complex",
    "reasoning": "你的分析理由（简短）",
    "suggested_steps": 0-10 (预估需要的步骤数)
}}

仅返回 JSON 对象，不要包含其他文本。"""

    def __init__(self, llm):
        """初始化决策器

        Args:
            llm: LLM 接口实例
        """
        self.llm = llm

    async def should_plan(self, task: str) -> PlanDecision:
        """判断任务是否需要预规划

        Args:
            task: 任务描述

        Returns:
            PlanDecision 对象，包含决策结果和理由
        """
        logger.info(f"Analyzing task complexity: {task[:50]}...")

        try:
            prompt = self.DECISION_PROMPT.format(task=task)

            response = self.llm.ask(
                [
                    {
                        "role": "system",
                        "content": "You are a task complexity analyzer.",
                    },
                    {"role": "user", "content": prompt},
                ]
            )

            # 解析响应
            if hasattr(response, "model_dump_json"):
                response_text = response.model_dump_json()
            elif hasattr(response, "thought"):
                # AgentResponse 类型
                response_text = str(response.thought)
            else:
                response_text = str(response)

            # 尝试从响应中提取 JSON
            decision = self._parse_decision(response_text)
            logger.info(
                f"Decision: needs_planning={decision.needs_planning}, "
                f"complexity={decision.complexity.value}"
            )
            return decision

        except Exception as e:
            logger.error(f"Failed to analyze task complexity: {e}")
            # 默认返回需要规划（保守策略）
            return PlanDecision(
                needs_planning=True,
                complexity=TaskComplexity.MODERATE,
                reasoning=f"Analysis failed ({e}), defaulting to planning",
                suggested_steps=5,
            )

    def should_plan_sync(self, task: str) -> PlanDecision:
        """同步版本的规划判断

        Args:
            task: 任务描述

        Returns:
            PlanDecision 对象
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在异步上下文中，使用线程池
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.should_plan(task))
                    return future.result()
            else:
                return loop.run_until_complete(self.should_plan(task))
        except RuntimeError:
            return asyncio.run(self.should_plan(task))

    def _parse_decision(self, response_text: str) -> PlanDecision:
        """解析 LLM 的决策响应

        Args:
            response_text: LLM 响应文本

        Returns:
            PlanDecision 对象
        """
        # 尝试直接解析 JSON
        try:
            # 尝试找到 JSON 对象
            text = response_text.strip()

            # 如果包含 ```json 标记，提取其中的内容
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()

            # 找到 JSON 对象的开始和结束
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                text = text[json_start:json_end]

            data = json.loads(text)

            complexity_str = data.get("complexity", "moderate").lower()
            complexity = TaskComplexity(complexity_str)

            return PlanDecision(
                needs_planning=data.get("needs_planning", True),
                complexity=complexity,
                reasoning=data.get("reasoning", ""),
                suggested_steps=data.get("suggested_steps", 5),
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(
                f"Failed to parse decision JSON: {e}, response: {response_text[:200]}"
            )
            # 基于关键词的简单判断作为后备
            return self._fallback_decision(response_text)

    def _fallback_decision(self, text: str) -> PlanDecision:
        """基于关键词的后备决策

        Args:
            text: 响应文本

        Returns:
            PlanDecision 对象
        """
        text_lower = text.lower()

        if "complex" in text_lower or "需要规划" in text or "多个步骤" in text:
            return PlanDecision(
                needs_planning=True,
                complexity=TaskComplexity.COMPLEX,
                reasoning="Detected complex task from keywords",
                suggested_steps=7,
            )
        elif "simple" in text_lower or "简单" in text or "直接执行" in text:
            return PlanDecision(
                needs_planning=False,
                complexity=TaskComplexity.SIMPLE,
                reasoning="Detected simple task from keywords",
                suggested_steps=2,
            )
        else:
            return PlanDecision(
                needs_planning=True,
                complexity=TaskComplexity.MODERATE,
                reasoning="Default to moderate complexity",
                suggested_steps=5,
            )
