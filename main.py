import sys
from elephan_code.llm import LLMFactory
from elephan_code.agent import CodingAgent
from elephan_code.tools import ToolManager


if __name__ == "__main__":
    llm = LLMFactory.get_llm(
        "openrouter", 
        api_key="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",
        model_id=sys.argv[2]
    )
    tools = ToolManager()
    agent = CodingAgent(llm, tools)

    agent.run(sys.argv[1])
