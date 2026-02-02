import json

from llm import LLMInterface
from tools import ToolManager


class CodingAgent:
    def __init__(self, llm: LLMInterface, tools: ToolManager):
        self.llm = llm
        self.tools = tools
        self.memory = [
            {"role": "system", "content": self._generage_system_prompt()}
        ]

    def _generage_system_prompt(self):
        return """You are a moduler AI Coding Agent.
        Response in JSON with 'thought' and 'action', for action you need return action name and action parameters.
        Available tools: read_file(path), write_file(path, content), excute_shell(command), finish.
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
        print(f"\n[Action]: {action.name}({action.parameters})")
        observation = self.tools.call(action.name, action.parameters)

        # 3. 观察
        print(f"\n[Observation]: {observation}...")
        self.memory.append({"role": "user", "content": f"Observation: {observation}"})

        return True

    def run(self, task):
        self.memory.append({"role": "user", "content": task})
        max_steps = 10
        for _ in range(max_steps):
            if not self.step():
                break
