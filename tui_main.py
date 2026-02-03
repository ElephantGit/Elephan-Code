import os
import sys
from typing import Optional
from elephan_code.llm import LLMFactory
from elephan_code.agent import Agent
from elephan_code.tools import ToolManager
from elephan_code.tui import ChatTUI


def _get_env_api_key() -> Optional[str]:
    return os.environ.get("OPENROUTER_API_KEY")


class TUIApp:
    def __init__(self, api_key: str, initial_model_id: str):
        self.api_key = api_key
        self.model_id = initial_model_id
        self.tools = ToolManager()
        self.agent: Optional[Agent] = None
        self.tui = ChatTUI()

        self._create_agent()
        self.tui._current_model_id = self.model_id
        self.tui._on_model_change = self._on_model_change

    def _create_agent(self):
        llm = LLMFactory.get_llm(
            "openrouter",
            api_key=self.api_key,
            model_id=self.model_id,
        )
        self.agent = Agent(llm, self.tools)
        self.tui.set_agent(self.agent)

    def _on_model_change(self, new_model_id: str):
        self.model_id = new_model_id
        self._create_agent()

    def run(self, start_task: Optional[str] = None):
        self.tui.print_welcome(self.model_id)
        self.tui.run(start_with_task=start_task)


def main():
    api_key = _get_env_api_key()
    if not api_key:
        print(
            "ERROR: OPENROUTER_API_KEY environment variable is not set.",
            file=sys.stderr,
        )
        sys.exit(2)

    model_id = "anthropic/claude-3.5-sonnet"
    if len(sys.argv) > 1:
        model_id = sys.argv[1]

    start_task = None
    if len(sys.argv) > 2:
        start_task = " ".join(sys.argv[2:])

    app = TUIApp(api_key, model_id)
    app.run(start_task)


if __name__ == "__main__":
    main()
