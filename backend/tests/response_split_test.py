"""Regression test for display metadata vs. speakable assistant text."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app import build_assistant_output


def main() -> int:
    response = {
        "ok": True,
        "provider": "ollama",
        "action": "chat",
        "message": "Hello! How can I help you today?",
        "data": {"content": "Hello! How can I help you today?"},
        "error": None,
        "route": {
            "language": "English",
            "provider": "Ollama",
            "model": "gemma3:1b",
            "source": "Local AI",
        },
    }
    output = build_assistant_output(response)

    blocked_terms = ("Language", "Provider", "Model", "Source", "Intent", "Execution")
    if output.assistant_message != "Hello! How can I help you today?":
        print("FAIL assistant message changed unexpectedly")
        return 1
    if any(term in output.assistant_message for term in blocked_terms):
        print("FAIL assistant message contains metadata")
        return 1
    if output.metadata["Provider"] != "Ollama":
        print("FAIL metadata was not preserved for display")
        return 1

    print("PASS response split keeps TTS text metadata-free")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
