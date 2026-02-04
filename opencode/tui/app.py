from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Button, Header, Input, Label, Select
from textual.binding import Binding

class CodeApp(App):
    """Main TUI application for the coding assistant."""
    
    CSS_PATH = 'styles.tcss'
    BINDINGS = [
        Binding('ctrl+c', 'quit', 'Quit', show=True),
        Binding('ctrl+s', 'toggle_model_selector', 'Select Model', show=True),
    ]
    
    def __init__(self):
        super().__init__()
        self.current_model = None
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Container(
            ScrollableContainer(id='chat-container'),
            Input(placeholder='Enter your request...', id='user-input'),
        )
        yield Container(
            Select(
                [(model, model) for model in ['GPT-3.5', 'GPT-4']],
                prompt='Select AI Model',
                value='GPT-3.5',
            ),
            id='model-selector',
        )
    
    def on_mount(self) -> None:
        """Handle app startup."""
        self.query_one('#user-input').focus()
    
    def action_toggle_model_selector(self) -> None:
        """Toggle the model selector visibility."""
        selector = self.query_one('#model-selector')
        selector.toggle_class('visible')
    
    async def on_input_submitted(self, message: Input.Submitted) -> None:
        """Handle user input submission."""
        user_input = message.value
        if not user_input.strip():
            return
            
        # Clear input
        input_widget = self.query_one('#user-input')
        input_widget.value = ''
        
        # Add user message to chat
        chat_container = self.query_one('#chat-container')
        chat_container.mount(Label(user_input, classes='user-message'))
        
        # TODO: Process user input and get AI response
        # This is where we'll integrate with the AI agent

if __name__ == '__main__':
    app = CodeApp()
    app.run()