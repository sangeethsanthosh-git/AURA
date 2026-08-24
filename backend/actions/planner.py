"""Rule-based action planner for AURA HANDS V1."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote_plus, urlparse

from backend.actions.models import ActionRequest, ActionType, RiskLevel
from backend.actions.registry import KNOWN_WEBSITES, ApplicationRegistry
from backend.actions.target_resolver import TargetResolver
from backend.actions.models import TargetType


class ActionPlanner:
    def __init__(self, app_registry: ApplicationRegistry | None = None) -> None:
        self.app_registry = app_registry or ApplicationRegistry()
        self.target_resolver = TargetResolver(self.app_registry)

    def plan(self, user_input: str) -> list[ActionRequest]:
        text = user_input.strip()
        normalized = " ".join(text.lower().split())

        if re.search(r"\b(delete|remove permanently|format drive|purchase|send email|send message|run command|powershell|cmd)\b", normalized):
            return [ActionRequest(ActionType.BLOCKED, text, risk_level=RiskLevel.BLOCKED)]

        ambiguous = self._ambiguous_open_action(text, normalized)
        if ambiguous:
            return [ambiguous]

        calculation = self._calculation_action(text)
        if calculation:
            return [calculation]

        typing = self._type_text_action(text)
        if typing:
            return [typing]

        media = self._media_action(text)
        if media:
            return [media]

        close = self._close_focus_action(text)
        if close:
            return [close]

        ui_action = self._ui_control_action(text)
        if ui_action:
            return [ui_action]

        search = self._search_action(text, normalized)
        if search:
            return [search]

        create = self._create_folder_action(text)
        if create:
            return [create]

        rename = self._rename_action(text)
        if rename:
            return [rename]

        copy = self._copy_move_action(text, move=False)
        if copy:
            return [copy]

        move = self._copy_move_action(text, move=True)
        if move:
            return [move]

        target_action = self._open_target_action(text)
        if target_action:
            return [target_action]

        website = self._website_action(text, normalized)
        if website:
            return [website]

        folder = self._open_folder_action(text, normalized)
        if folder:
            return [folder]

        app = self._application_action(text, normalized)
        if app:
            return [app]

        file_action = self._open_file_action(text)
        if file_action:
            return [file_action]

        return []

    def validate_llm_suggestion(self, suggestion: dict[str, object]) -> ActionRequest | None:
        allowed = {"action_type", "application", "url", "query", "path", "source", "destination", "new_name"}
        if set(suggestion) - allowed:
            return None
        action_type = suggestion.get("action_type")
        if action_type == "open_application" and isinstance(suggestion.get("application"), str):
            app = self.app_registry.resolve(str(suggestion["application"]))
            return ActionRequest(ActionType.OPEN_APPLICATION, app.key if app else str(suggestion["application"])) if app else None
        if action_type == "open_website" and isinstance(suggestion.get("url"), str):
            url = str(suggestion["url"])
            return ActionRequest(ActionType.OPEN_WEBSITE, url) if self._valid_url(url) else None
        return None

    def _application_action(self, text: str, normalized: str) -> ActionRequest | None:
        match = re.match(r"^(open|launch|start)\s+(.+?)[.!?]?$", text, flags=re.IGNORECASE)
        if not match:
            return None
        target = match.group(2).strip()
        resolved = self.target_resolver.resolve(target, TargetType.APPLICATION)
        if resolved.target_type == TargetType.UNKNOWN and re.search(r"https?://", target, flags=re.IGNORECASE):
            return None
        if resolved.target_type == TargetType.APPLICATION and resolved.confidence >= 0.8:
            return ActionRequest(ActionType.OPEN_APPLICATION, resolved.target, {"display_name": resolved.display_name})
        if resolved.error:
            return ActionRequest(ActionType.OPEN_APPLICATION, resolved.target, {"resolution_error": resolved.error})
        if "." not in target and "/" not in target and "\\" not in target and "folder" not in normalized:
            return ActionRequest(ActionType.OPEN_APPLICATION, target)
        return None

    def _open_target_action(self, text: str) -> ActionRequest | None:
        match = re.match(r"^(open|launch|start|go to|visit)\s+(.+?)[.!?]?$", text, flags=re.IGNORECASE)
        if not match:
            return None
        target = match.group(2).strip()
        preferred = self.target_resolver.preferred_type_from_text(target)
        resolved = self.target_resolver.resolve(target, preferred)
        if resolved.target_type == TargetType.WEBSITE or resolved.target_type == TargetType.URL:
            return ActionRequest(ActionType.OPEN_WEBSITE, resolved.target, {"label": resolved.display_name or target, "target_type": resolved.target_type.value})
        if resolved.target_type == TargetType.APPLICATION and resolved.confidence >= 0.8:
            return ActionRequest(ActionType.OPEN_APPLICATION, resolved.target, {"display_name": resolved.display_name, "target_type": resolved.target_type.value})
        if resolved.target_type == TargetType.FILE:
            return ActionRequest(ActionType.OPEN_FILE, resolved.target, {"target_type": resolved.target_type.value})
        if resolved.target_type == TargetType.FOLDER:
            return ActionRequest(ActionType.OPEN_FOLDER, resolved.target, {"target_type": resolved.target_type.value})
        return None

    @staticmethod
    def _ambiguous_open_action(text: str, normalized: str) -> ActionRequest | None:
        if re.fullmatch(r"open\s+(?:a\s+|the\s+)?(?:file|folder|document)", normalized):
            target = normalized.removeprefix("open ").strip()
            return ActionRequest(
                ActionType.BLOCKED,
                target,
                {"ambiguity": "missing_target", "clarification": f"Which {target} would you like me to open?"},
                risk_level=RiskLevel.BLOCKED,
            )
        return None

    def _website_action(self, text: str, normalized: str) -> ActionRequest | None:
        match = re.match(r"^(open|go to|visit)\s+(.+?)[.!?]?$", text, flags=re.IGNORECASE)
        if not match:
            return None
        target = match.group(2).strip()
        key = target.lower().replace(" ", "")
        url = KNOWN_WEBSITES.get(key) or target
        if "." in url and not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        if self._valid_url(url):
            return ActionRequest(ActionType.OPEN_WEBSITE, url, {"label": target})
        return None

    def _search_action(self, text: str, normalized: str) -> ActionRequest | None:
        match = re.match(r"^search(?:\s+(google|youtube|web))?\s+(?:for\s+)?(.+)$", text, flags=re.IGNORECASE)
        if not match:
            return None
        engine = (match.group(1) or "google").lower()
        query = match.group(2).strip(" .!?")
        base = "https://www.youtube.com/results?search_query=" if engine == "youtube" else "https://www.google.com/search?q="
        return ActionRequest(ActionType.WEB_SEARCH, query, {"engine": engine, "url": base + quote_plus(query)})

    def _media_action(self, text: str) -> ActionRequest | None:
        match = re.match(r"^(play|pause|stop|next|previous|resume)(?:\s+(?:music|media|song|track))?(?:\s+(?:on|in)?\s*(.+?))?[.!?]?$", text, flags=re.IGNORECASE)
        if not match:
            return None
        verb = match.group(1).lower()
        target = (match.group(2) or "active_media_app").strip() or "active_media_app"
        if target.lower() in {"music", "media", "song", "track"}:
            target = "active_media_app"
        action_type = {
            "play": ActionType.PLAY_MEDIA,
            "resume": ActionType.PLAY_MEDIA,
            "pause": ActionType.PAUSE_MEDIA,
            "stop": ActionType.STOP_MEDIA,
            "next": ActionType.NEXT_MEDIA,
            "previous": ActionType.PREVIOUS_MEDIA,
        }[verb]
        if target != "active_media_app":
            app = self.app_registry.resolve(target)
            target = app.key if app else target
        return ActionRequest(action_type, target, {"requested_action": verb})

    def _close_focus_action(self, text: str) -> ActionRequest | None:
        match = re.match(r"^(close|quit|focus|switch to)\s+(.+?)[.!?]?$", text, flags=re.IGNORECASE)
        if not match:
            return None
        verb = match.group(1).lower()
        target = match.group(2).strip()
        app = self.app_registry.resolve(target)
        target = app.key if app else target
        action_type = ActionType.CLOSE_APPLICATION if verb in {"close", "quit"} else ActionType.FOCUS_APPLICATION
        return ActionRequest(action_type, target, {"requested_action": verb})

    @staticmethod
    def _ui_control_action(text: str) -> ActionRequest | None:
        match = re.match(r"^(click|double click|press|scroll|wait)(?:\s+(.+?))?[.!?]?$", text, flags=re.IGNORECASE)
        if not match:
            return None
        verb = match.group(1).lower()
        target = (match.group(2) or "").strip() or verb
        action_type = {
            "click": ActionType.CLICK,
            "double click": ActionType.CLICK,
            "press": ActionType.PRESS_KEY,
            "scroll": ActionType.SCROLL,
            "wait": ActionType.WAIT,
        }[verb]
        return ActionRequest(action_type, target, {"requested_action": verb})

    def _calculation_action(self, text: str) -> ActionRequest | None:
        expression = self._calculation_expression(text)
        if expression is None:
            return None
        return ActionRequest(ActionType.CALCULATE, expression, {"expression": expression})

    @classmethod
    def _calculation_expression(cls, text: str) -> str | None:
        lowered = text.lower().strip()
        if not re.search(r"\b(add|plus|calculate|compute|multiply|times|minus|subtract|divide|percent|%)\b|[-+*/]\s*\d", lowered):
            return None
        cleaned = re.sub(r"^(?:and\s+|then\s+|next\s+|after that\s+)?", "", text, flags=re.IGNORECASE).strip()
        starts_with_add = bool(re.match(r"add\s+", cleaned, flags=re.IGNORECASE))
        cleaned = re.sub(r"^(?:add|calculate|compute|what is|solve)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\bplus\b", "+", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\badd\b", "+", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\btimes\b|\bmultiplied by\b|\bmultiply\b", "*", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bminus\b|\bsubtract\b", "-", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bdivided by\b|\bdivide\b", "/", cleaned, flags=re.IGNORECASE)
        if starts_with_add:
            cleaned = re.sub(r"(?<=\d)\s+and\s+(?=\d)", " + ", cleaned, flags=re.IGNORECASE)
        else:
            cleaned = re.sub(r"\band\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bpercent of\b", "% of", cleaned, flags=re.IGNORECASE)
        cleaned = " ".join(cleaned.split()).strip(" .!?")
        if re.search(r"\d", cleaned):
            return cleaned
        return None

    def _type_text_action(self, text: str) -> ActionRequest | None:
        match = re.match(r"^(?:write|type|enter)\s+(.+?)[.!?]?$", text, flags=re.IGNORECASE)
        if not match:
            return None
        content = match.group(1).strip().strip('"')
        return ActionRequest(ActionType.TYPE_TEXT, content, {"text": content}, risk_level=RiskLevel.SAFE)

    def _open_folder_action(self, text: str, normalized: str) -> ActionRequest | None:
        shortcuts = {
            "downloads": Path.home() / "Downloads",
            "documents": Path.home() / "Documents",
            "desktop": Path.home() / "Desktop",
        }
        for name, path in shortcuts.items():
            if re.search(rf"\b(open|show)\b.*\b{name}\b", normalized):
                return ActionRequest(ActionType.OPEN_FOLDER, str(path))
        match = re.match(r"^(open|show)\s+(.+?)\s+folder[.!?]?$", text, flags=re.IGNORECASE)
        if match:
            return ActionRequest(ActionType.OPEN_FOLDER, str(Path(match.group(2)).expanduser()))
        return None

    def _open_file_action(self, text: str) -> ActionRequest | None:
        match = re.match(r"^open\s+(?:file\s+)?(.+\.[\w]{1,8})[.!?]?$", text, flags=re.IGNORECASE)
        return ActionRequest(ActionType.OPEN_FILE, str(Path(match.group(1)).expanduser())) if match else None

    def _create_folder_action(self, text: str) -> ActionRequest | None:
        match = re.match(r"^create\s+(?:a\s+)?folder(?:\s+called|\s+named)?\s+(.+?)[.!?]?$", text, flags=re.IGNORECASE)
        if not match:
            return None
        name = match.group(1).strip().strip('"')
        target = Path.home() / "Documents" / name if not any(sep in name for sep in ("\\", "/")) else Path(name).expanduser()
        return ActionRequest(ActionType.CREATE_FOLDER, str(target), risk_level=RiskLevel.CONFIRMATION_REQUIRED, requires_confirmation=True)

    def _rename_action(self, text: str) -> ActionRequest | None:
        match = re.match(r"^rename\s+(?:file\s+)?(.+?)\s+to\s+(.+?)[.!?]?$", text, flags=re.IGNORECASE)
        if not match:
            return None
        return ActionRequest(
            ActionType.RENAME_FILE,
            str(Path(match.group(1)).expanduser()),
            {"new_name": match.group(2).strip()},
            RiskLevel.CONFIRMATION_REQUIRED,
            True,
        )

    def _copy_move_action(self, text: str, move: bool) -> ActionRequest | None:
        verb = "move" if move else "copy"
        match = re.match(rf"^{verb}\s+(?:file\s+)?(.+?)\s+to\s+(.+?)[.!?]?$", text, flags=re.IGNORECASE)
        if not match:
            return None
        return ActionRequest(
            ActionType.MOVE_FILE if move else ActionType.COPY_FILE,
            str(Path(match.group(1)).expanduser()),
            {"destination": str(Path(match.group(2)).expanduser())},
            RiskLevel.CONFIRMATION_REQUIRED,
            True,
        )

    @staticmethod
    def _valid_url(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and " " not in parsed.netloc
