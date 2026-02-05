from __future__ import annotations

from elephan_code.agent import Agent
from elephan_code.llm import LLMFactory
from elephan_code.tools import ToolManager

from .config import AppConfig


class AppRuntime:
    """Container for the core runtime objects used by app entrypoints."""

    def __init__(self, llm, tools: ToolManager, agent: Agent):
        self.llm = llm
        self.tools = tools
        self.agent = agent



def build_runtime(config: AppConfig) -> AppRuntime:
    """Build LLM, tools, and agent from a single config object."""
    llm = LLMFactory.get_llm(
        config.provider,
        api_key=config.api_key,
        model_id=config.model_id,
    )
    tools = ToolManager()
    agent = Agent(llm, tools, mode=config.mode, max_steps=config.max_steps)
    return AppRuntime(llm=llm, tools=tools, agent=agent)
