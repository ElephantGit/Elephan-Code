import sys
import os

# Ensure project root is on sys.path so local package imports work when running this script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from elephan_code.llm.llm import AgentResponse, ActionModel
from elephan_code.agent import Agent
from elephan_code.tools import ToolManager


class FakeLLM:
    def __init__(self, seq):
        self.seq = seq
        self.i = 0

    def ask(self, messages):
        if self.i >= len(self.seq):
            return self.seq[-1]
        r = self.seq[self.i]
        self.i += 1
        return r


def main():
    seq = [
        AgentResponse(
            thought="I will write a file",
            action=ActionModel(name="write_file", parameters={"path": "smoke.txt", "content": "hello from agent"})
        ),
        AgentResponse(
            thought="I will run a command",
            action=ActionModel(name="excute_shell", parameters={"command": "echo smoke"})
        ),
        AgentResponse(
            thought="done",
            action=ActionModel(name="finish", parameters={})
        ),
    ]

    llm = FakeLLM(seq)
    tools = ToolManager()
    # 使用轨迹记录器并保存到 runs/
    from elephan_code.utils.trajectory import TrajectoryRecorder
    recorder = TrajectoryRecorder(save_dir="runs")
    agent = Agent(llm, tools)
    agent.trajectory = recorder

    agent.run("smoke test")

    # show saved trajectory
    try:
        from elephan_code.utils.logging import get_logger

        lg = get_logger("elephan.scripts.smoke_test")
        path = recorder._auto_path()
        lg.info("[Smoke Verify] trajectory saved to: %s", path)
        lg.info(open(path, 'r', encoding='utf-8').read())
    except Exception:
        pass

    # verify file written
    try:
        from elephan_code.utils.logging import get_logger
        lg = get_logger("elephan.scripts.smoke_test")
        with open("smoke.txt", "r", encoding="utf-8") as f:
            lg.info("[Smoke Verify] file content: %s", f.read())
    except Exception as e:
        lg.error("[Smoke Verify] file not found or error: %s", e)


if __name__ == '__main__':
    main()
