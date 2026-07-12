import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from aura_config import OLLAMA_HOST, OLLAMA_THINK

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class OllamaMessage:
    role: str
    content: str


@dataclass(frozen=True)
class OllamaChatResponse:
    content: str
    thinking: str | None
    raw_content: str
    raw: dict[str, Any]


class OllamaClient:
    def __init__(
        self,
        host: str = OLLAMA_HOST,
        think: bool | str = OLLAMA_THINK,
        timeout: int = 180,
    ) -> None:
        self.host = host.rstrip("/")
        self.think = think
        self.timeout = timeout

    def chat(
        self,
        model: str,
        messages: list[OllamaMessage],
        stream: bool = False,
    ) -> OllamaChatResponse:
        if stream:
            raise NotImplementedError("Streaming is not enabled in this console app yet.")

        payload = {
            "model": model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "stream": False,
            "think": self.think,
        }

        LOGGER.debug("Ollama chat request: %s", payload)
        raw = self._post_json("/api/chat", payload)
        LOGGER.debug("Ollama raw response: %s", raw)

        message = raw.get("message", {})
        raw_content = str(message.get("content", "")).strip()
        api_thinking = message.get("thinking")
        content, embedded_thinking = self._final_content(raw_content)
        thinking = api_thinking or embedded_thinking

        return OllamaChatResponse(
            content=content,
            thinking=thinking,
            raw_content=raw_content,
            raw=raw,
        )

    @staticmethod
    def _final_content(content: str) -> tuple[str, str | None]:
        close_tag = "</think>"
        if close_tag not in content:
            return content.strip(), None

        thinking, _, final = content.rpartition(close_tag)
        thinking = thinking.removeprefix("<think>").strip()
        final = final.strip()
        return final, thinking or None

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.host}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not connect to Ollama at {self.host}.") from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ollama returned invalid JSON: {body}") from exc
