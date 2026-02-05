import os
import sys
import asyncio
import argparse
from typing import Optional
from rich.console import Console
from elephan_code.llm import LLMFactory
from elephan_code.agent import Agent
from elephan_code.tools import ToolManager
from elephan_code.tui import ChatTUI
from elephan_code.tui.plan_mode_integration import PlanModeDisplayIntegration


def _get_env_api_key() -> Optional[str]:
    return os.environ.get("OPENROUTER_API_KEY")


def _parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Elephant Code Agent - TUI 版本")
    parser.add_argument("task", nargs="?", default=None, help="初始任务（可选）")
    parser.add_argument(
        "--model",
        "-m",
        default="anthropic/claude-3.5-sonnet",
        help="LLM 模型 ID，默认为 claude-3.5-sonnet",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "standard", "plan"],
        default="auto",
        help="执行模式：auto(自动，推荐)、standard(标准) 或 plan(计划)，默认为 auto",
    )
    parser.add_argument(
        "--max-steps", type=int, default=10, help="最大执行步数，默认为 10"
    )

    return parser.parse_args()


class TUIApp:
    def __init__(
        self,
        api_key: str,
        initial_model_id: str,
        mode: str = "auto",
        max_steps: int = 10,
    ):
        self.api_key = api_key
        self.model_id = initial_model_id
        self.mode = mode
        self.max_steps = max_steps
        self.tools = ToolManager()
        self.agent: Optional[Agent] = None
        self.tui = ChatTUI()
        self.console = Console()

        self._create_agent()
        self.tui._current_model_id = self.model_id
        self.tui._on_model_change = self._on_model_change

    def _create_agent(self):
        llm = LLMFactory.get_llm(
            "openrouter",
            api_key=self.api_key,
            model_id=self.model_id,
        )
        self.agent = Agent(llm, self.tools, mode=self.mode, max_steps=self.max_steps)
        self.tui.set_agent(self.agent)

    def _on_model_change(self, new_model_id: str):
        self.model_id = new_model_id
        self._create_agent()

    async def run_with_mode(self, task: str):
        if self.agent is None:
            self.console.print("[bold red]Agent not initialized[/bold red]")
            return {"success": False, "error": "Agent not initialized"}

        mode = self.agent.get_execution_mode()
        if mode is None:
            self.console.print("[bold red]Execution mode not available[/bold red]")
            return {"success": False, "error": "Mode not available"}

        mode_label = {
            "auto": "🤖 Auto Mode (智能模式)",
            "plan": "📋 Plan Mode (计划模式)",
            "standard": "⚡ Standard Mode (标准模式)",
        }.get(self.mode, self.mode)

        self.console.print("\n" + "=" * 60)
        self.console.print(f"[bold cyan]{mode_label}[/bold cyan]")
        self.console.print("=" * 60 + "\n")

        integration = PlanModeDisplayIntegration(self.console)
        integration.setup_callbacks(mode)

        self.console.print(f"[cyan]任务: {task}[/cyan]\n")

        try:
            result = await mode.run(task, max_steps=self.max_steps)

            if result.get("success"):
                self.console.print("\n[bold green]✅ 任务执行成功[/bold green]")
                if result.get("used_planning"):
                    self.console.print("[dim]执行方式: 使用预规划[/dim]")
                elif result.get("decision"):
                    self.console.print("[dim]执行方式: 直接执行（任务简单）[/dim]")
            else:
                self.console.print("\n[bold yellow]⚠️ 任务部分完成[/bold yellow]")

            return result

        except Exception as e:
            self.console.print(f"\n[bold red]❌ 执行出错: {e}[/bold red]")
            import traceback

            self.console.print("[dim]" + traceback.format_exc() + "[/dim]")
            return {"success": False, "error": str(e)}

    def run(self, start_task: Optional[str] = None):
        if self.mode in ("auto", "plan"):
            return asyncio.run(self.run_with_mode(start_task))
        else:
            self.tui.print_welcome(self.model_id)
            self.tui.run(start_with_task=start_task)


def main():
    args = _parse_arguments()

    api_key = _get_env_api_key()
    if not api_key:
        print(
            "ERROR: OPENROUTER_API_KEY environment variable is not set.",
            file=sys.stderr,
        )
        sys.exit(2)

    app = TUIApp(api_key, args.model, mode=args.mode, max_steps=args.max_steps)
    app.run(args.task)


if __name__ == "__main__":
    main()
