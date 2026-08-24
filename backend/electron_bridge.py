"""Controlled JSON-lines bridge for the Electron desktop UI."""

from __future__ import annotations

import json
import sys
import traceback
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if "AURA_APP_ROOT" in __import__("os").environ:
    PROJECT_ROOT = Path(__import__("os").environ["AURA_APP_ROOT"]).resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from ui.controller.aura_controller import AuraController  # noqa: E402


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "value"):
        return value.value
    return str(value)


def emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, default=_json_default, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def command(controller: AuraController, name: str, payload: dict[str, Any] | None) -> Any:
    payload = payload or {}
    if name == "status":
        return {"backend": "READY"}
    if name == "sendMessage":
        return asdict(controller.process_user_message(str(payload.get("message", ""))))
    if name == "listMemories":
        return controller.list_memories()
    if name == "forgetMemory":
        return asdict(controller.forget_memory(str(payload.get("content", ""))))
    if name == "activities":
        return [asdict(item) for item in controller.activities]
    if name == "providerStatus":
        return controller.provider_status()
    if name == "voiceState":
        return {"state": str(controller.voice_state.value)}
    if name == "startVoice":
        return asdict(controller.start_voice_recording())
    if name == "stopVoice":
        return asdict(controller.stop_voice_recording())
    raise ValueError(f"Unsupported command: {name}")


def main() -> int:
    try:
        controller = AuraController()
        emit({"event": {"type": "AURA_READY"}})
    except Exception as exc:
        emit({"event": {"type": "AURA_ERROR", "message": str(exc)}})
        return 1

    for line in sys.stdin:
        try:
            request = json.loads(line)
            request_id = str(request.get("id", ""))
            result = command(controller, str(request.get("command", "")), request.get("payload"))
            emit({"id": request_id, "ok": True, "result": result})
        except Exception as exc:
            emit({"id": str(locals().get("request", {}).get("id", "")), "ok": False, "error": str(exc)})
            traceback.print_exc(file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
