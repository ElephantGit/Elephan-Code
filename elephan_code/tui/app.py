"""Main Textual TUI application for Elephan-Code."""

import json
import asyncio
from typing import Optional, Callable
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Header, Footer, Input, Static
from textual import on, log, events
from textual.reactive import reactive

from elephan_code.tui.common import ModelConfig
from elephan_code.tui.widgets import (
    UserMessage,
    ThoughtMessage,
    ActionMessage,
    ObservationMessage,
    ErrorMessage,
    AssistantMessage,
    SystemMessage,
    StatusBar,
)


class ElephantApp(App):
    """Elephan-Code AI Programming Assistant - Textual TUI."""

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear_screen", "Clear"),
        ("ctrl+q", "quit", "Quit"),
        ("escape", "cancel_input", "Cancel"),
    ]

    current_state = reactive("idle")

    def __init__(self, api_key: str = "", model_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.model_id = model_id or ModelConfig().get_default()
        self._agent = None
        self._tools = None
        self._model_config = ModelConfig()
        self._on_model_change: Optional[Callable[[str], None]] = None
        self._current_input = ""
        self._is_processing = False

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()
        yield VerticalScroll(id="chat-container")
        yield Static("", id="model-selector")
        yield Input(
            placeholder="Enter your message or /models to switch model...",
            id="user-input",
        )
        yield StatusBar()

    def on_mount(self) -> None:
        """Handle app mount."""
        status_bar = self.query_one(StatusBar)
        status_bar.set_model(self.model_id)
        status_bar.set_state("idle")
        self._add_system_message(f"Welcome to Elephan-Code AI Programming Assistant!")
        self._add_system_message(f"Current model: {self.model_id}")
        self._add_system_message("Type /models to switch model, ^C to exit")

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        input_text = event.value.strip()
        if not input_text:
            return

        event.input.value = ""

        # Handle commands
        if input_text.startswith("/"):
            self._handle_command(input_text)
            return

        # Handle user message
        self._add_user_message(input_text)
        self._process_user_input(input_text)

    def action_quit(self) -> None:
        """Quit the application."""
        self._add_system_message("Goodbye!")
        self.exit()

    def action_clear_screen(self) -> None:
        """Clear the message history."""
        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_container.remove_children()
        self._add_system_message("Screen cleared")

    def action_cancel_input(self) -> None:
        """Cancel current input."""
        input_widget = self.query_one(Input)
        input_widget.value = ""
        input_widget.focus()

    def _handle_command(self, command: str) -> None:
        """Handle special commands."""
        cmd = command.lower().strip()

        if cmd in ("/models", "/model"):
            self._show_model_selector()
        elif cmd == "/help":
            self._show_help()
        elif cmd == "/clear":
            self.action_clear_screen()
        else:
            self._add_error_message(f"Unknown command: {command}")

    def _show_help(self) -> None:
        """Show help message."""
        help_text = """
Available Commands:
  /models  - Select and switch between AI models
  /clear   - Clear the screen
  /help    - Show this help message
Keyboard Shortcuts:
  ^C / ^Q  - Quit
  ^L       - Clear screen
  ESC      - Cancel input
        """
        self._add_system_message(help_text.strip())

    def _show_model_selector(self) -> None:
        """Show model selection UI."""
        models = self._model_config.get_models()

        selector_text = "\nAvailable Models:\n"
        for i, model in enumerate(models):
            marker = " ✓" if model["id"] == self.model_id else ""
            selector_text += f"  [{i + 1}] {model['name']}{marker}\n"
        selector_text += f"  [0] Cancel\n"

        self._add_system_message(selector_text.strip())

        # Store state for model selection
        self._awaiting_model_selection = True

    def _process_user_input(self, text: str) -> None:
        """Process user input and run agent."""
        if self._is_processing:
            self._add_error_message("Already processing, please wait...")
            return

        self._is_processing = True
        self.current_state = "thinking"

        # Run agent in background
        asyncio.create_task(self._run_agent(text))

    async def _run_agent(self, task: str) -> None:
        """Run agent for a task."""
        try:
            if self._agent is None:
                self._add_error_message(
                    "Agent not initialized. Please restart the app."
                )
                return

            # Add user message to agent memory
            self._agent.memory.append({"role": "user", "content": task})

            # Run agent steps
            max_steps = 10
            steps = 0
            while steps < max_steps:
                should_continue = self._agent.step()
                if not should_continue:
                    break
                steps += 1

                # Small delay to let UI update
                await asyncio.sleep(0.01)

        except Exception as e:
            self._add_error_message(f"Error: {e}")
        finally:
            self._is_processing = False
            self.current_state = "idle"
            await asyncio.sleep(0.1)

    def watch_current_state(self, old_state: str, new_state: str) -> None:
        """Watch current state changes."""
        status_bar = self.query_one(StatusBar)
        status_bar.set_state(new_state)

    def _scroll_to_bottom(self) -> None:
        """Scroll chat container to bottom."""
        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_container.scroll_end(animate=False)

    # Message widget helpers
    def _add_user_message(self, content: str) -> None:
        """Add user message widget."""
        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_container.mount(UserMessage(content))
        self._scroll_to_bottom()

    def _add_thought_message(self, content: str) -> None:
        """Add thought message widget."""
        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_container.mount(ThoughtMessage(content))
        self._scroll_to_bottom()

    def _add_action_message(self, name: str, params: dict) -> None:
        """Add action message widget."""
        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_container.mount(ActionMessage(name, params))
        self._scroll_to_bottom()

    def _add_observation_message(self, content: str) -> None:
        """Add observation message widget."""
        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_container.mount(ObservationMessage(content))
        self._scroll_to_bottom()

    def _add_error_message(self, content: str) -> None:
        """Add error message widget."""
        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_container.mount(ErrorMessage(content))
        self._scroll_to_bottom()

    def _add_assistant_message(self, content: str) -> None:
        """Add assistant message widget."""
        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_container.mount(AssistantMessage(content))
        self._scroll_to_bottom()

    def _add_system_message(self, content: str) -> None:
        """Add system message widget."""
        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_container.mount(SystemMessage(content))
        self._scroll_to_bottom()

    # Agent callback methods
    def _on_thought(self, text: str) -> None:
        """Handle agent thought callback."""
        self.call_from_thread(self._add_thought_message, text)

    def _on_action(self, name: str, params: dict) -> None:
        """Handle agent action callback."""
        self.call_from_thread(self._add_action_message, name, params)

    def _on_observation(self, text: str) -> None:
        """Handle agent observation callback."""
        self.call_from_thread(self._add_observation_message, text)

    # Public API for integration
    def set_agent(self, agent) -> None:
        """Set the agent instance and wire up callbacks."""
        self._agent = agent
        if agent and hasattr(agent, "on_thought"):
            agent.on_thought = self._on_thought
        if agent and hasattr(agent, "on_action"):
            agent.on_action = self._on_action
        if agent and hasattr(agent, "on_observation"):
            agent.on_observation = self._on_observation

    def set_model_change_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for model changes."""
        self._on_model_change = callback

    def change_model(self, model_id: str) -> None:
        """Change the current model."""
        if model_id == self.model_id:
            self._add_system_message(f"Already using {model_id}")
            return

        self.model_id = model_id
        status_bar = self.query_one(StatusBar)
        status_bar.set_model(model_id)
        self._add_system_message(f"Switched to model: {model_id}")

        if self._on_model_change:
            self._on_model_change(model_id)
