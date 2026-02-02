import sys
from llm import LLMFactory
from agent import CodingAgent
from tools import ToolManager


if __name__ == "__main__":
    llm = LLMFactory.get_llm(
        "openrouter", 
        api_key="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",
        model_id=sys.argv[2]
    )
    tools = ToolManager()
    agent = CodingAgent(llm, tools)

    agent.run(sys.argv[1])
