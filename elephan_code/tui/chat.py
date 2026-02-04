import json
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.syntax import Syntax
from typing import Optional, Callable, Any, List, Dict


class ModelConfig:
    """模型配置管理器"""

    def __init__(self):
        self.config_path = Path(__file__).parent.parent / "config" / "models.json"
        self._config: Dict = {}
        self._load_config()

    def _load_config(self):
        """加载模型配置"""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        else:
            # 默认配置
            self._config = {
                "default": "anthropic/claude-3.5-sonnet",
                "models": [
                    {
                        "id": "anthropic/claude-3.5-sonnet",
                        "name": "Claude 3.5 Sonnet",
                        "description": "Default model",
                    }
                ],
            }

    def get_models(self) -> List[Dict]:
        """获取所有可用模型"""
        return self._config.get("models", [])

    def get_default(self) -> str:
        """获取默认模型ID"""
        return self._config.get("default", "anthropic/claude-3.5-sonnet")

    def get_model_by_index(self, index: int) -> Optional[Dict]:
        """根据索引获取模型"""
        models = self.get_models()
        if 0 <= index < len(models):
            return models[index]
        return None


class ChatTUI:
    def __init__(self):
        self.console = Console()
        self._on_step_callback: Optional[Callable[[], bool]] = None
        self._agent_instance = None
        self._model_config = ModelConfig()
        self._current_model_id: str = ""
        self._api_key: str = ""
        self._tools = None
        self._on_model_change: Optional[Callable[[str], None]] = None

    def print_welcome(self, model_name: str = ""):
        self.console.print()
        self.console.print(
            Panel(
                Text("Elephan-Code AI Programming Assistant", style="bold cyan"),
                title="Welcome",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        self.console.print()
        self.console.print("[dim]交互式终端界面 | Interactive Terminal UI[/dim]")
        if model_name:
            self.console.print(f"[dim]Model: {model_name}[/dim]")
        self.console.print(
            "[dim]输入 'exit' 或 'quit' 退出 | Type 'exit' or 'quit' to exit[/dim]"
        )
        self.console.print()

    def print_thought(self, text: str):
        self.console.print()
        self.console.print(
            Panel(text, title="[Thought]", border_style="blue", padding=(0, 1))
        )

    def print_action(self, name: str, params: Any):
        params_str = (
            json.dumps(params, ensure_ascii=False, indent=2) if params else "{}"
        )
        content = Text()
        content.append(f"{name}(", style="yellow")
        content.append(params_str, style="dim yellow")
        content.append(")", style="yellow")

        self.console.print()
        self.console.print(
            Panel(content, title="[Action]", border_style="yellow", padding=(0, 1))
        )

    def print_observation(self, text: str):
        self.console.print()
        self.console.print(
            Panel(text, title="[Observation]", border_style="green", padding=(0, 1))
        )

    def print_error(self, text: str):
        self.console.print()
        self.console.print(
            Panel(
                Text(text, style="red"),
                title="[Error]",
                border_style="red",
                padding=(0, 1),
            )
        )

    def print_assistant(self, text: str):
        self.console.print()
        self.console.print(
            Panel(text, title="Assistant", border_style="cyan", padding=(0, 1))
        )

    def print_user(self, text: str):
        self.console.print()
        self.console.print(
            Panel(text, title="You", border_style="white", padding=(0, 1))
        )

    def print_separator(self):
        self.console.print()
        self.console.print("[dim]" + "=" * 60 + "[/dim]")
        self.console.print()

    def print_models_list(self):
        table = Table(title="Available Models", border_style="cyan")
        table.add_column("#", style="bold cyan", width=4)
        table.add_column("Model", style="bold")
        table.add_column("Description", style="dim")

        models = self._model_config.get_models()
        for i, model in enumerate(models):
            marker = " ✓" if model["id"] == self._current_model_id else ""
            table.add_row(
                str(i + 1), f"{model['name']}{marker}", model.get("description", "")
            )

        self.console.print()
        self.console.print(table)
        self.console.print()
        self.console.print("[dim]Enter number to select, or 'q' to cancel[/dim]")

    def handle_models_command(self) -> bool:
        self.print_models_list()

        try:
            choice = self.console.input(
                "[bold cyan]Select model[/bold cyan] > "
            ).strip()

            if choice.lower() in ("q", "quit", "cancel", ""):
                self.console.print("[dim]Cancelled[/dim]")
                return False

            try:
                index = int(choice) - 1
                model = self._model_config.get_model_by_index(index)

                if model is None:
                    self.print_error(f"Invalid selection: {choice}")
                    return False

                if model["id"] == self._current_model_id:
                    self.console.print(f"[dim]Already using {model['name']}[/dim]")
                    return False

                self._current_model_id = model["id"]
                self.console.print()
                self.console.print(
                    Panel(
                        f"Switched to [bold]{model['name']}[/bold]\n[dim]{model['id']}[/dim]",
                        title="Model Changed",
                        border_style="green",
                        padding=(0, 1),
                    )
                )

                if self._on_model_change:
                    self._on_model_change(model["id"])

                return True

            except ValueError:
                self.print_error(f"Invalid input: {choice}")
                return False

        except (EOFError, KeyboardInterrupt):
            self.console.print()
            self.console.print("[dim]Cancelled[/dim]")
            return False

    def prompt_user(self) -> Optional[str]:
        try:
            user_input = self.console.input("[bold cyan]You[/bold cyan] > ")
            stripped = user_input.strip()

            if stripped.lower() in ("exit", "quit"):
                return None

            return stripped if stripped else None
        except (EOFError, KeyboardInterrupt):
            return None

    def _on_thought(self, text: str):
        self.print_thought(text)

    def _on_action(self, name: str, params: dict):
        self.print_action(name, params)

    def _on_observation(self, text: str):
        self.print_observation(text)

    def set_agent(self, agent):
        self._agent_instance = agent
        if agent and hasattr(agent, "on_thought"):
            agent.on_thought = self._on_thought
        if agent and hasattr(agent, "on_action"):
            agent.on_action = self._on_action
        if agent and hasattr(agent, "on_observation"):
            agent.on_observation = self._on_observation

    def run_one_turn(self, task: str):
        if self._agent_instance is None:
            self.print_error("Agent not set. Please set agent before running.")
            return False

        self.print_user(task)

        try:
            self._agent_instance.memory.append({"role": "user", "content": task})
            return True
        except Exception as e:
            self.print_error(f"Error processing task: {e}")
            return False

    def _is_command(self, text: str) -> bool:
        return text.startswith("/")

    def _handle_command(self, text: str) -> bool:
        cmd = text.lower().strip()

        if cmd in ("/models", "/model"):
            self.handle_models_command()
            return True
        elif cmd == "/help":
            self._show_help()
            return True
        else:
            self.print_error(
                f"Unknown command: {text}\nType /help for available commands"
            )
            return True

    def _show_help(self):
        help_text = """[bold]Available Commands:[/bold]

  /models  - Select and switch between AI models
  /help    - Show this help message
  exit     - Exit the application"""
        self.console.print()
        self.console.print(
            Panel(help_text, title="Help", border_style="cyan", padding=(0, 1))
        )
        self.console.print()

    def run(self, start_with_task: Optional[str] = None):
        if start_with_task:
            self.run_one_turn(start_with_task)

        while True:
            user_input = self.prompt_user()

            if user_input is None:
                self.console.print()
                self.console.print("[dim]Goodbye![/dim]")
                self.console.print()
                break

            if self._is_command(user_input):
                self._handle_command(user_input)
                continue

            if not self.run_one_turn(user_input):
                continue

            max_steps = getattr(self._agent_instance, "max_steps", 10)
            steps = 0
            while steps < max_steps:
                try:
                    should_continue = self._agent_instance.step()
                    if not should_continue:
                        break
                    steps += 1
                except Exception as e:
                    self.print_error(f"Error during step: {e}")
                    break

            self.print_separator()
