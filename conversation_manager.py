import logging
from dataclasses import dataclass, field

from language_manager import LanguageManager
from model_router import ModelRouter, ModelSelection
from ollama_client import OllamaClient, OllamaMessage
from backend.personality import AURAPersonality, DEFAULT_PERSONALITY
from backend.session_context import SessionContext

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
        personality: AURAPersonality = DEFAULT_PERSONALITY,
        session_context: SessionContext | None = None,
    ) -> None:
        self.language_manager = language_manager
        self.model_router = model_router
        self.ollama_client = ollama_client or OllamaClient()
        self.personality = personality
        self.session_context = session_context or SessionContext()
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
            self.session_context.add_turn("user", user_text)
            self.session_context.add_turn("assistant", language_reply)
            return language_reply, selection

        detected_language = self.language_manager.detect_text_language(user_text)
        if detected_language == "ml" and not self.language_manager.is_locked:
            self.language_manager.set_language("ml", manually_locked=False)
        elif detected_language == "mixed" and not self.language_manager.is_locked:
            self.language_manager.set_language("en", manually_locked=False)

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
        self.session_context.add_turn("user", user_text)
        self.session_context.add_turn("assistant", assistant_text)
        return assistant_text, selection

    def add_message(self, role: str, content: str) -> None:
        self.state.messages.append(Message(role=role, content=content))

    def _build_messages(self) -> list[OllamaMessage]:
        messages = [
            OllamaMessage(
                role="system",
                content=self.personality.system_prompt(
                    self.language_manager.system_prompt(),
                    self.session_context.relevant_context_for(self.state.messages[-1].content if self.state.messages else ""),
                ),
            )
        ]

        for message in self.state.messages[-12:]:
            messages.append(OllamaMessage(role=message.role, content=message.content))

        return messages
