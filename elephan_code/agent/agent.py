import json
import typing

from elephan_code.llm.llm import LLMInterface
from elephan_code.tools import ToolManager


class Agent:
    def __init__(self, llm: LLMInterface, tools: ToolManager):
        self.llm = llm
        self.tools = tools
        self.memory = [
            {"role": "system", "content": self._generage_system_prompt()}
        ]

    def _generage_system_prompt(self):
        return """You are a moduler AI Coding Agent.
        Response in JSON with 'thought' and 'action', for action you need return action name and action parameters.
        Available tools: read_file(path), write_file(path, content), excute_shell(command) (alias: execute_shell), finish.
        YOU MUST ONLY RESPOND IN VALID JSON!
        """

    def step(self):
        # 1. 思考
        response_data = self.llm.ask(self.memory)
        self.memory.append({"role": "assistant", "content": json.dumps(response_data.model_dump_json())})

        print(f"\n[Thought]: {response_data.thought}")

        action = response_data.action
        if action.name == 'finish':
            return False # 任务结束

        # 2. 行动
        # 尝试把 parameters 转为字典（兼容 pydantic model 或原始 dict）
        try:
            params = action.parameters if isinstance(action.parameters, dict) else (
                action.parameters.model_dump() if hasattr(action.parameters, 'model_dump') else (
                    action.parameters.dict() if hasattr(action.parameters, 'dict') else {}
                )
            )
        except Exception:
            params = {}

        print(f"\n[Action]: {action.name}({params})")
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

        print(f"\n[Observation]: {obs_str}...")
        self.memory.append({"role": "user", "content": f"Observation: {obs_str}"})

        return True

    def run(self, task):
        self.memory.append({"role": "user", "content": task})
        max_steps = 10
        for _ in range(max_steps):
            if not self.step():
                break
