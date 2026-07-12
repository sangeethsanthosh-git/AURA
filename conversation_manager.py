import logging
from dataclasses import dataclass, field

from language_manager import LanguageManager
from model_router import ModelRouter, ModelSelection
from ollama_client import OllamaClient, OllamaMessage

LOGGER = logging.getLogger(__name__)


@dataclass
class Message:
    role: str
    content: str


@dataclass
class ConversationState:
    messages: list[Message] = field(default_factory=list)
    selected_model: str | None = None


class ConversationManager:
    def __init__(
        self,
        language_manager: LanguageManager,
        model_router: ModelRouter,
        ollama_client: OllamaClient | None = None,
    ) -> None:
        self.language_manager = language_manager
        self.model_router = model_router
        self.ollama_client = ollama_client or OllamaClient()
        self.state = ConversationState()

    def ask(self, user_text: str) -> tuple[str, ModelSelection]:
        language_reply = self.language_manager.handle_language_command(user_text)
        if language_reply is not None:
            selection = self.model_router.select_model(
                self.language_manager.current_language
            )
            self.state.selected_model = selection.model
            self.add_message("user", user_text)
            self.add_message("assistant", language_reply)
            return language_reply, selection

        selection = self.model_router.select_model(self.language_manager.current_language)
        self.state.selected_model = selection.model
        self.add_message("user", user_text)

        LOGGER.debug("Sending prompt to Ollama with model %s", selection.model)

        try:
            result = self.ollama_client.chat(
                model=selection.model,
                messages=self._build_messages(),
                stream=False,
            )
        except RuntimeError as exc:
            LOGGER.exception("Ollama request failed.")
            raise

        assistant_text = result.content
        self.add_message("assistant", assistant_text)
        return assistant_text, selection

    def add_message(self, role: str, content: str) -> None:
        self.state.messages.append(Message(role=role, content=content))

    def _build_messages(self) -> list[OllamaMessage]:
        messages = [
            OllamaMessage(
                role="system",
                content=self.language_manager.system_prompt(),
            )
        ]

        for message in self.state.messages[-12:]:
            messages.append(OllamaMessage(role=message.role, content=message.content))

        return messages
