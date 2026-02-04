from textual.containers import Container
from textual.widgets import Label, Static

class MessageContainer(Container):
    """Container for displaying chat messages with different styles."""
    
    DEFAULT_CSS = """
    MessageContainer {
        width: 100%;
        height: auto;
        margin: 1 0;
    }
    """
    
    def __init__(self, message: str, message_type: str = 'system'):
        super().__init__()
        self.message = message
        self.message_type = message_type
    
    def compose(self):
        yield Label(self.message, classes=f'{self.message_type}-message')

class ThoughtMessage(MessageContainer):
    """Display AI thought process messages."""
    def __init__(self, message: str):
        super().__init__(message, 'thought')

class ActionMessage(MessageContainer):
    """Display AI action messages."""
    def __init__(self, message: str):
        super().__init__(message, 'action')

class ObservationMessage(MessageContainer):
    """Display observation messages."""
    def __init__(self, message: str):
        super().__init__(message, 'observation')

class UserMessage(MessageContainer):
    """Display user input messages."""
    def __init__(self, message: str):
        super().__init__(message, 'user')

class AssistantMessage(MessageContainer):
    """Display assistant response messages."""
    def __init__(self, message: str):
        super().__init__(message, 'assistant')

class SystemMessage(MessageContainer):
    """Display system messages."""
    def __init__(self, message: str):
        super().__init__(message, 'system')
