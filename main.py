import os
import sys
from elephan_code.llm import LLMFactory
from elephan_code.agent import Agent
from elephan_code.tools import ToolManager


def _get_env_api_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <task> <model_id>")
        sys.exit(1)

    api_key = _get_env_api_key()
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY environment variable is not set.")
        sys.exit(2)

    task = sys.argv[1]
    model_id = sys.argv[2]

    llm = LLMFactory.get_llm(
        "openrouter",
        api_key=api_key,
        model_id=model_id,
    )

    tools = ToolManager()
    agent = Agent(llm, tools)

    agent.run(task)
