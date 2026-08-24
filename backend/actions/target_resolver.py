"""Target resolution for Hands actions."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from backend.actions.models import ResolvedTarget, TargetType
from backend.actions.registry import KNOWN_WEBSITES, ApplicationRegistry


class TargetResolver:
    """Separates application, website, URL, file, and folder targets."""

    def __init__(self, app_registry: ApplicationRegistry | None = None) -> None:
        self.app_registry = app_registry or ApplicationRegistry()

    def resolve(self, phrase: str, preferred_type: TargetType | None = None) -> ResolvedTarget:
        raw = phrase.strip().strip('"').strip(" .!?")
        normalized = " ".join(raw.lower().split())
        if raw.startswith(("http://", "https://")):
            if self._valid_url(raw):
                return ResolvedTarget(TargetType.URL, raw, 0.98, metadata={"raw": raw})
            return ResolvedTarget(TargetType.UNKNOWN, raw, 0.0, metadata={"raw": raw}, error="Invalid URL.")
        path = Path(raw).expanduser()
        if preferred_type == TargetType.FILE or (path.suffix and any(sep in raw for sep in ("\\", "/"))):
            return ResolvedTarget(TargetType.FILE, str(path), 0.88, metadata={"raw": raw})
        if preferred_type == TargetType.FOLDER or normalized.endswith(" folder"):
            target = re.sub(r"\bfolder\b", "", raw, flags=re.IGNORECASE).strip()
            return ResolvedTarget(TargetType.FOLDER, str(Path(target).expanduser()), 0.84, metadata={"raw": raw})
        if preferred_type == TargetType.URL or self._valid_url(raw):
            url = raw if raw.startswith(("http://", "https://")) else f"https://{raw}"
            return ResolvedTarget(TargetType.URL, url, 0.98, metadata={"raw": raw})
        website_name = self._website_name(normalized)
        if preferred_type == TargetType.WEBSITE or website_name:
            key = website_name or normalized
            url = KNOWN_WEBSITES.get(key.replace(" ", "")) or f"https://{key.replace(' ', '')}.com/"
            return ResolvedTarget(TargetType.WEBSITE, url, 0.9, display_name=key, metadata={"raw": raw})
        app_phrase = self._application_name(raw)
        app = self.app_registry.resolve(app_phrase)
        if preferred_type is None and normalized.replace(" ", "") in KNOWN_WEBSITES:
            if app and self.app_registry.launch_command(app):
                return ResolvedTarget(TargetType.APPLICATION, app.key, 0.88, app.name, {"raw": raw, "defaulted_to_installed_app": True})
            return ResolvedTarget(
                TargetType.WEBSITE,
                KNOWN_WEBSITES[normalized.replace(" ", "")],
                0.86,
                display_name=normalized,
                metadata={"raw": raw, "defaulted_to_website": True},
            )
        if app:
            return ResolvedTarget(TargetType.APPLICATION, app.key, 0.95, app.name, {"raw": raw})
        if preferred_type == TargetType.APPLICATION:
            return ResolvedTarget(TargetType.APPLICATION, app_phrase, 0.35, app_phrase, {"raw": raw}, f"Application not found: {app_phrase}")
        return ResolvedTarget(TargetType.UNKNOWN, raw, 0.0, metadata={"raw": raw}, error="Unknown target type.")

    @staticmethod
    def preferred_type_from_text(text: str) -> TargetType | None:
        lowered = text.lower()
        if re.search(r"\b(web\s*site|website|web page|site)\b", lowered):
            return TargetType.WEBSITE
        if re.search(r"\b(app|application|desktop app|desktop application)\b", lowered):
            return TargetType.APPLICATION
        if re.search(r"https?://|\w+\.\w{2,}", text):
            return TargetType.URL
        return None

    @staticmethod
    def _application_name(text: str) -> str:
        text = re.sub(r"^(?:open|launch|start)\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(?:the|app|application|desktop app|desktop application)\b", " ", text, flags=re.IGNORECASE)
        return " ".join(text.split()).strip(" .!?")

    @staticmethod
    def _website_name(normalized: str) -> str | None:
        if "website" in normalized or "web site" in normalized or "site" in normalized:
            return re.sub(r"\b(?:website|web site|site|the)\b", " ", normalized).strip()
        return None

    @staticmethod
    def _valid_url(url: str) -> bool:
        candidate = url if url.startswith(("http://", "https://")) else f"https://{url}"
        parsed = urlparse(candidate)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and " " not in parsed.netloc and "." in parsed.netloc
