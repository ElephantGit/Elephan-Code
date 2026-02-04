"""Custom Textual widgets for Elephan-Code TUI."""

from textual.widgets import Static
from textual.containers import Horizontal
from textual import log


class MessageWidget(Static):
    """Base widget for all message types."""

    def __init__(self, content: str, **kwargs):
        super().__init__(content, **kwargs)


class UserMessage(MessageWidget):
    """User input message with white border."""

    def __init__(self, content: str, **kwargs):
        super().__init__(content, **kwargs)
        self.add_class("user-message")


class ThoughtMessage(MessageWidget):
    """AI thought message with blue border."""

    def __init__(self, content: str, **kwargs):
        formatted = f"💭 {content}"
        super().__init__(formatted, **kwargs)
        self.add_class("thought-message")


class ActionMessage(MessageWidget):
    """Tool action message with yellow border."""

    def __init__(self, name: str, params: dict, **kwargs):
        import json

        params_str = (
            json.dumps(params, ensure_ascii=False, indent=2) if params else "{}"
        )
        formatted = f"🔧 {name}(\n{params_str}\n)"
        super().__init__(formatted, **kwargs)
        self.add_class("action-message")


class ObservationMessage(MessageWidget):
    """Observation result message with green border."""

    def __init__(self, content: str, **kwargs):
        formatted = f"👁 {content}"
        super().__init__(formatted, **kwargs)
        self.add_class("observation-message")


class ErrorMessage(MessageWidget):
    """Error message with red border."""

    def __init__(self, content: str, **kwargs):
        formatted = f"❌ {content}"
        super().__init__(formatted, **kwargs)
        self.add_class("error-message")


class AssistantMessage(MessageWidget):
    """Assistant response message with cyan border."""

    def __init__(self, content: str, **kwargs):
        super().__init__(content, **kwargs)
        self.add_class("assistant-message")


class SystemMessage(MessageWidget):
    """System message with gray border."""

    def __init__(self, content: str, **kwargs):
        formatted = f"ℹ️ {content}"
        super().__init__(formatted, **kwargs)
        self.add_class("system-message")


class StatusBar(Horizontal):
    """Status bar displaying model and state."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        padding: 0 1;
    }
    StatusBar #model-label {
        width: 30%;
        color: $success;
        text-style: bold;
    }
    StatusBar #state-label {
        width: 20%;
    }
    StatusBar #state-label.idle {
        color: $text-muted;
    }
    StatusBar #state-label.running {
        color: $warning;
        text-style: bold;
    }
    StatusBar #state-label.error {
        color: $error;
        text-style: bold;
    }
    StatusBar #shortcuts-label {
        width: 50%;
        text-align: right;
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._model_id = ""
        self._state = "idle"

    def compose(self):
        from textual.widgets import Static

        yield Static("Model: ---", id="model-label")
        yield Static("Idle", id="state-label", classes="idle")
        yield Static("^Q quit | ^L clear | /models", id="shortcuts-label")

    def set_model(self, model_id: str):
        """Update model display."""
        self._model_id = model_id
        # Format model name for display (remove provider prefix)
        display_name = model_id.split("/")[-1] if "/" in model_id else model_id
        self.query_one("#model-label", Static).update(f"Model: {display_name}")

    def set_state(self, state: str):
        """Update state display."""
        self._state = state
        label = self.query_one("#state-label", Static)
        label.remove_class("idle", "running", "error")

        state_map = {
            "idle": ("Idle", "idle"),
            "running": ("Running...", "running"),
            "error": ("Error", "error"),
            "thinking": ("Thinking...", "running"),
        }

        text, css_class = state_map.get(state.lower(), (state.capitalize(), "idle"))
        label.update(text)
        label.add_class(css_class)
