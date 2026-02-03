import json
import typing

from elephan_code.llm.llm import LLMInterface
from elephan_code.llm.prompt_manager import PromptManager
from elephan_code.tools import ToolManager
from elephan_code.utils.trajectory import TrajectoryRecorder
from elephan_code.utils.logging import get_logger

logger = get_logger("elephan.agent")


class Agent:
    def __init__(self, llm: LLMInterface, tools: ToolManager):
        self.llm = llm
        self.tools = tools
        # 初始化 PromptManager，传入当前可用工具名称
        try:
            tool_names = (
                list(self.tools.tools.keys()) if hasattr(self.tools, "tools") else []
            )
        except Exception:
            tool_names = []

        self.prompt_manager = PromptManager(tools=tool_names)

        # 生成系统提示并放入初始内存
        schema_constraint = None
        try:
            if hasattr(self.llm, "_get_system_prompt_constraint"):
                schema_constraint = self.llm._get_system_prompt_constraint()
        except Exception:
            schema_constraint = None

        self.memory = [
            {
                "role": "system",
                "content": self.prompt_manager.compose(
                    schema_constraint=schema_constraint
                ),
            }
        ]
        # 可选的轨迹记录器
        self.trajectory: TrajectoryRecorder | None = None
        # 回调机制用于 TUI 实时输出
        self.on_thought = None
        self.on_action = None
        self.on_observation = None

    def _generage_system_prompt(self):
        # 兼容旧接口：委托给 PromptManager 生成系统提示
        schema_constraint = None
        try:
            if hasattr(self.llm, "_get_system_prompt_constraint"):
                schema_constraint = self.llm._get_system_prompt_constraint()
        except Exception:
            schema_constraint = None

        return self.prompt_manager.compose(schema_constraint=schema_constraint)

    def step(self):
        # 1. 思考
        response_data = self.llm.ask(self.memory)
        self.memory.append(
            {
                "role": "assistant",
                "content": json.dumps(response_data.model_dump_json()),
            }
        )

        logger.info("[Thought]: %s", response_data.thought)

        if self.on_thought:
            self.on_thought(str(response_data.thought))

        # 轨迹记录：thought
        try:
            if self.trajectory:
                self.trajectory.record_thought(str(response_data.thought))
        except Exception:
            pass

        action = response_data.action
        if action.name == "finish":
            return False  # 任务结束

        # 2. 行动
        # 尝试把 parameters 转为字典（兼容 pydantic model 或原始 dict）
        try:
            params = (
                action.parameters
                if isinstance(action.parameters, dict)
                else (
                    action.parameters.model_dump()
                    if hasattr(action.parameters, "model_dump")
                    else (
                        action.parameters.dict()
                        if hasattr(action.parameters, "dict")
                        else {}
                    )
                )
            )
        except Exception:
            params = {}

        logger.info("[Action]: %s(%s)", action.name, params)

        if self.on_action:
            self.on_action(action.name, params)

        # 轨迹记录：action
        try:
            if self.trajectory:
                self.trajectory.record_action(action.name, params)
        except Exception:
            pass
        observation = self.tools.call(action.name, params)

        # 3. 观察 — 支持新的 ToolResult 结构或兼容旧字符串
        obs_str = None
        try:
            # 延迟导入以避免循环依赖问题
            from elephan_code.tools.base_tool import ToolResult as _ToolResult

            if isinstance(observation, _ToolResult):
                if observation.success:
                    if isinstance(observation.data, str):
                        obs_str = observation.data
                    else:
                        obs_str = json.dumps(observation.data, ensure_ascii=False)
                else:
                    obs_str = f"Error: {observation.error}"
            else:
                obs_str = str(observation)
        except Exception:
            obs_str = str(observation)

        logger.info("[Observation]: %s", obs_str)

        if self.on_observation:
            self.on_observation(obs_str)

        # 轨迹记录：observation
        try:
            if self.trajectory:
                self.trajectory.record_observation(obs_str)
        except Exception:
            pass

        self.memory.append({"role": "user", "content": f"Observation: {obs_str}"})

        return True

    def run(self, task):
        self.memory.append({"role": "user", "content": task})
        if self.trajectory:
            self.trajectory.start(task)
        max_steps = 10
        for _ in range(max_steps):
            if not self.step():
                break
        if self.trajectory:
            self.trajectory.end(status="completed")
