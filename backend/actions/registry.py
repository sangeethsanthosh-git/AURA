"""Application and website registries for controlled launches."""

from __future__ import annotations

import platform
import re
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Iterable


@dataclass(frozen=True)
class ApplicationEntry:
    key: str
    name: str
    aliases: tuple[str, ...]
    windows_commands: tuple[str, ...]
    allow_windows_alias: bool = False


class ApplicationRegistry:
    """Central lookup for launchable desktop applications."""

    def __init__(self, entries: tuple[ApplicationEntry, ...] | None = None) -> None:
        self.entries = entries or (
            ApplicationEntry("chrome", "Google Chrome", ("chrome", "google chrome"), ("chrome", "chrome.exe")),
            ApplicationEntry("edge", "Microsoft Edge", ("edge", "microsoft edge"), ("msedge", "msedge.exe")),
            ApplicationEntry("vscode", "Visual Studio Code", ("vs code", "vscode", "visual studio code", "code"), ("code", "code.cmd")),
            ApplicationEntry("calculator", "Calculator", ("calculator", "calc"), ("calc.exe",), True),
            ApplicationEntry("notepad", "Notepad", ("notepad",), ("notepad.exe",), True),
            ApplicationEntry("spotify", "Spotify", ("spotify",), ("spotify", "spotify.exe")),
        )
        self._aliases = {
            alias.lower(): entry
            for entry in self.entries
            for alias in (entry.key, entry.name, *entry.aliases)
        }
        self._discovered: dict[str, ApplicationEntry] | None = None

    def resolve(self, name: str) -> ApplicationEntry | None:
        normalized = self.normalize_name(name)
        if normalized in self._aliases:
            return self._aliases[normalized]
        discovered = self._discovered_entries()
        if normalized in discovered:
            return discovered[normalized]
        return self._best_discovered_match(normalized, discovered.values())

    def launch_command(self, entry: ApplicationEntry) -> str | None:
        if platform.system() != "Windows":
            return None
        for command in entry.windows_commands:
            found = which(command)
            if found:
                return found
        if entry.allow_windows_alias:
            for command in entry.windows_commands:
                if command.endswith(".exe"):
                    return command
        return None

    @classmethod
    def normalize_name(cls, name: str) -> str:
        text = " ".join(name.lower().strip().split())
        text = re.sub(r"^(?:open|launch|start)\s+", "", text)
        text = re.sub(r"\b(?:the|app|application|desktop app|desktop application)\b", " ", text)
        text = re.sub(r"\s+", " ", text).strip(" .!?")
        aliases = {"calc": "calculator", "vs code": "vscode", "visual studio code": "vscode", "chrome browser": "google chrome"}
        return aliases.get(text, text)

    def _discovered_entries(self) -> dict[str, ApplicationEntry]:
        if self._discovered is not None:
            return self._discovered
        discovered: dict[str, ApplicationEntry] = {}
        for name, command in self._windows_start_menu_shortcuts():
            key = self.normalize_name(name)
            if not key or key in discovered:
                continue
            discovered[key] = ApplicationEntry(key, name, (key,), (command,))
        for name, command in self._windows_app_paths():
            key = self.normalize_name(name)
            if not key or key in discovered:
                continue
            discovered[key] = ApplicationEntry(key, name, (key,), (command,))
        self._discovered = discovered
        return discovered

    @staticmethod
    def _windows_start_menu_shortcuts() -> Iterable[tuple[str, str]]:
        if platform.system() != "Windows":
            return []
        roots = [
            Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs",
            Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
        ]
        shortcuts: list[tuple[str, str]] = []
        for root in roots:
            if not root.exists():
                continue
            for shortcut in root.rglob("*.lnk"):
                shortcuts.append((shortcut.stem, str(shortcut)))
        return shortcuts

    @staticmethod
    def _windows_app_paths() -> Iterable[tuple[str, str]]:
        if platform.system() != "Windows":
            return []
        try:
            import winreg
        except ImportError:
            return []
        roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        ]
        entries: list[tuple[str, str]] = []
        for hive, subkey in roots:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    for index in range(winreg.QueryInfoKey(key)[0]):
                        child_name = winreg.EnumKey(key, index)
                        with winreg.OpenKey(key, child_name) as child:
                            command = str(winreg.QueryValue(child, None) or "")
                            if command:
                                entries.append((Path(child_name).stem, command.strip('"')))
            except OSError:
                continue
        return entries

    @staticmethod
    def _best_discovered_match(normalized: str, entries: Iterable[ApplicationEntry]) -> ApplicationEntry | None:
        terms = set(normalized.split())
        if not terms:
            return None
        best: tuple[float, ApplicationEntry] | None = None
        for entry in entries:
            names = {entry.key, entry.name.lower(), *entry.aliases}
            score = max((len(terms & set(name.split())) / max(1, len(terms | set(name.split()))) for name in names), default=0.0)
            if score >= 0.75 and (best is None or score > best[0]):
                best = (score, entry)
        return best[1] if best else None


KNOWN_WEBSITES = {
    "youtube": "https://www.youtube.com/",
    "chatgpt": "https://chatgpt.com/",
    "github": "https://github.com/",
    "google": "https://www.google.com/",
    "gmail": "https://mail.google.com/",
    "spotify": "https://open.spotify.com/",
}
