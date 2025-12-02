"""
An App to show the current time.
"""

from datetime import datetime
import requests
from textual.app import App, ComposeResult
from textual.widgets import Label, Input, Button, Collapsible, ContentSwitcher, Footer, Header, Pretty, Markdown, ListView
from textual.containers import ScrollableContainer, VerticalGroup, HorizontalGroup, Vertical, Horizontal

API_URL = "https://leekwars.com/api"

def get_session_token(username: str, password: str):
    session = requests.Session()
    response = session.post(
        f"{API_URL}/farmer/login-token",
        data={"login": username, "password" : password}
    )
    response.raise_for_status()
    return session, response.json()

class LWApp(App):
    TITLE = "Leek Wars Toolbox"
    CSS = """
    Screen { align: center middle; }
    Digits { width: auto; }
    #chat {
           
    }
    Markdown {
        padding: 0;
        margin: 0 0 0 2;
    }
    Markdown > MarkdownParagraph {
        margin: 0 0 0 0;
    }
    """
    session: requests.Session = None

    def compose(self) -> ComposeResult:
        yield Header()
        #yield Label("Leek Wars toolbox")
        with Collapsible(title="Account", id="account_collapse"):
            yield Input(type="text", id="username")
            yield Input(type="text", id="password", password=bool)
            yield Button("LOG IN", id="button_login")
        with ContentSwitcher():
            pass
        with Vertical():
            yield ScrollableContainer(id="chat", classes="chat")
            with Vertical():
                yield Input(type="text", id="chat-input")
                yield Button("Send", id="button_send_chat")
                
        yield Footer()

    def on_ready(self) -> None:
        self.set_interval(5, self.refresh_chat)
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        #self.exit()
        if event.button.id == "button_login":
            self.login()
        if event.button.id == "button_send_chat":
            self.send_chat_message()

    def login(self):
        self.session = None
        username = self.query_one("#username", Input).value
        password = self.query_one("#password", Input).value
        self.session, data = get_session_token(username, password)
        self.query_one("#account_collapse").title = username
        self.query_one("#password", Input).value = ""
        self.refresh_chat()
        #self.exit(data["farmer"]["id"])

    def send_chat_message(self):
        chat_input = self.query_one("#chat-input")
        self.session.post(
            f"{API_URL}/message/send-message",
            data={"conversation_id": 1, "message": chat_input.value}
        )
        chat_input.value = ""
        self.refresh_chat()

    async def refresh_chat(self):
        if (not self.session):
            return
        response = self.session.get(f"{API_URL}/message/get-messages/1/50/0").json()
        container = self.query_one("#chat", ScrollableContainer)
        for child in container.children:
            child.remove()
        messages = response["messages"]
        for message in messages:
            message_widget = VerticalGroup(classes="chat-message")
            container.mount(message_widget)
            if message["farmer"]["id"] == 0:
                farmer_name = "BOT"
            else:
                farmer_name = message["farmer"]["name"]
            message_widget.mount(Label(farmer_name))
            message_widget.mount(Markdown(message["content"].strip()))
            reactions = " ".join(list(message["reactions"].keys()))
            message_widget.mount(Label(reactions))
        
if __name__ == "__main__":
    app = LWApp()
    reply = app.run()
    print(reply)
