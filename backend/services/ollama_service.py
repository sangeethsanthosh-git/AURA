"""
Service to handle communication with the local Ollama LLM.
Supports persistent HTTP keep-alive sessions, streaming inference,
multi-turn chat context, timeouts, and cancellation.
"""

from typing import Optional, List, Dict, Iterator
import json
import threading
import requests
import logging
from backend.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_CONTEXT_LENGTH,
    OLLAMA_REQUEST_TIMEOUT,
    OLLAMA_KEEP_ALIVE,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class OllamaService:
    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        context_length: int = OLLAMA_CONTEXT_LENGTH,
        timeout: float = OLLAMA_REQUEST_TIMEOUT,
        keep_alive: str = OLLAMA_KEEP_ALIVE,
    ):
        # Avoid 2s Windows IPv6 [::1] fallback delay when 'localhost' is passed
        normalized_url = base_url.rstrip("/").replace("://localhost:", "://127.0.0.1:")
        if normalized_url.endswith("://localhost"):
            normalized_url = normalized_url.replace("://localhost", "://127.0.0.1")

        self.base_url = normalized_url
        self.model = model
        self.context_length = context_length
        self.timeout = timeout
        self.keep_alive = keep_alive
        self._thread_local = threading.local()

    def _get_session(self) -> requests.Session:
        """Return a thread-local HTTP keep-alive session."""
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = requests.Session()
            self._thread_local.session = session
        return session

    def check_connection(self) -> bool:
        """Check if Ollama server is running and reachable."""
        try:
            res = self._get_session().get(f"{self.base_url}/api/version", timeout=3.0)
            return res.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama connection check failed: {e}")
            return False

    def check_model_available(self, model_name: Optional[str] = None) -> bool:
        """Check if the configured model is installed locally in Ollama."""
        target = model_name or self.model
        try:
            res = self._get_session().get(f"{self.base_url}/api/tags", timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name") for m in data.get("models", [])]
                return any(
                    m == target or m.startswith(f"{target}:") or target.startswith(f"{m}:")
                    for m in models
                )
        except Exception as e:
            logger.warning(f"Error checking model availability: {e}")
        return False

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        stream: bool,
    ) -> dict:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        return {
            "model": self.model,
            "messages": full_messages,
            "stream": stream,
            "keep_alive": self.keep_alive,
            "options": {
                "num_ctx": self.context_length,
                "temperature": 0.7,
            },
        }

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = SYSTEM_PROMPT,
        cancel_event: Optional[threading.Event] = None,
    ) -> Iterator[str]:
        """
        Stream assistant tokens incrementally from Ollama /api/chat.
        Aborts cleanly if cancel_event is set.
        """
        url = f"{self.base_url}/api/chat"
        payload = self._build_payload(messages, system_prompt, stream=True)

        try:
            with self._get_session().post(
                url, json=payload, stream=True, timeout=self.timeout
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if cancel_event is not None and cancel_event.is_set():
                        break
                    if not line:
                        continue
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break
        except requests.exceptions.Timeout:
            logger.error("Ollama streaming chat request timed out.")
            yield "I am sorry, the request to the language model timed out."
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama.")
            yield "I am unable to connect to Ollama. Please make sure the Ollama service is running."
        except Exception as e:
            logger.error(f"Error during Ollama streaming chat: {e}")
            yield f"An error occurred: {str(e)}"

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = SYSTEM_PROMPT,
    ) -> str:
        """
        Send a multi-turn conversation list to Ollama via /api/chat.
        Each item in messages: {'role': 'user' | 'assistant', 'content': '...'}
        """
        url = f"{self.base_url}/api/chat"
        payload = self._build_payload(messages, system_prompt, stream=False)

        try:
            response = self._get_session().post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            message = data.get("message", {})
            return message.get("content", "").strip()
        except requests.exceptions.Timeout:
            logger.error("Ollama chat request timed out.")
            return "I am sorry, the request to the language model timed out."
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama.")
            return "I am unable to connect to Ollama. Please make sure the Ollama service is running."
        except Exception as e:
            logger.error(f"Error during Ollama chat: {e}")
            return f"An error occurred: {str(e)}"

    def generate_response(
        self,
        prompt: str,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> str:
        """Single-turn generation wrapper."""
        return self.chat([{"role": "user", "content": prompt}], system_prompt)
