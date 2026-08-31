"""Validated local action execution for AURA HANDS V1."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import webbrowser
from pathlib import Path

from backend.actions.models import ActionExecutionStatus, ActionRequest, ActionResult, ActionType
from backend.actions.registry import ApplicationRegistry
from backend.router.math_engine import MathEngine


class ActionExecutor:
    def __init__(self, app_registry: ApplicationRegistry | None = None) -> None:
        self.app_registry = app_registry or ApplicationRegistry()
        self.math_engine = MathEngine()

    def execute(self, action: ActionRequest) -> ActionResult:
        started = time.perf_counter()
        try:
            if action.action_type == ActionType.OPEN_APPLICATION:
                return self._open_application(action, started)
            if action.action_type == ActionType.OPEN_WEBSITE:
                return self._open_url(action, action.target, started)
            if action.action_type == ActionType.WEB_SEARCH:
                return self._open_url(action, str(action.parameters["url"]), started)
            if action.action_type == ActionType.CALCULATE:
                return self._calculate(action, started)
            if action.action_type == ActionType.TYPE_TEXT:
                return self._type_text(action, started)
            if action.action_type in {
                ActionType.CLOSE_APPLICATION,
                ActionType.FOCUS_APPLICATION,
                ActionType.PLAY_MEDIA,
                ActionType.PAUSE_MEDIA,
                ActionType.STOP_MEDIA,
                ActionType.NEXT_MEDIA,
                ActionType.PREVIOUS_MEDIA,
                ActionType.PRESS_KEY,
                ActionType.CLICK,
                ActionType.SCROLL,
                ActionType.WAIT,
            }:
                return self._not_implemented(action, started)
            if action.action_type == ActionType.OPEN_FOLDER:
                return self._open_path(action, started, expected_dir=True)
            if action.action_type == ActionType.OPEN_FILE:
                return self._open_path(action, started, expected_dir=False)
            if action.action_type == ActionType.CREATE_FOLDER:
                return self._create_folder(action, started)
            if action.action_type == ActionType.RENAME_FILE:
                return self._rename_file(action, started)
            if action.action_type == ActionType.COPY_FILE:
                return self._copy_file(action, started)
            if action.action_type == ActionType.MOVE_FILE:
                return self._move_file(action, started)
            return self._failure(action, "This action is blocked in AURA HANDS V1.", started, ActionExecutionStatus.BLOCKED.value)
        except PermissionError:
            return self._failure(action, "Permission denied.", started)
        except OSError as exc:
            return self._failure(action, str(exc), started)

    def _open_application(self, action: ActionRequest, started: float) -> ActionResult:
        entry = self.app_registry.resolve(action.target)
        if not entry:
            return self._failure(action, f"I do not know how to open application: {action.target}.", started)
        command = self.app_registry.launch_command(entry)
        if not command:
            return self._failure(action, f"{entry.name} is not available on this computer.", started)
        if command.lower().endswith(".lnk") or Path(command).exists():
            os.startfile(command)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(command, shell=True, close_fds=True)
        return self._success(action, f"Opened {entry.name}.", "Windows application launcher", started, {"application": entry.key})

    def _open_url(self, action: ActionRequest, url: str, started: float) -> ActionResult:
        opened = webbrowser.open(url, new=2)
        if not opened:
            return self._failure(action, "The default browser could not open that URL.", started)
        return self._success(action, f"Opened {url}.", "Default browser", started, {"url": url})

    def _open_path(self, action: ActionRequest, started: float, expected_dir: bool) -> ActionResult:
        path = Path(action.target).expanduser()
        if expected_dir and not path.is_dir():
            return self._failure(action, f"Folder not found: {path}", started)
        if not expected_dir and not path.is_file():
            return self._failure(action, f"File not found: {path}", started)
        os.startfile(str(path))  # type: ignore[attr-defined]
        kind = "folder" if expected_dir else "file"
        return self._success(action, f"Opened {kind}: {path}", "Windows ShellExecute", started)

    def _create_folder(self, action: ActionRequest, started: float) -> ActionResult:
        path = Path(action.target).expanduser()
        if path.exists():
            return self._failure(action, f"Destination already exists: {path}", started)
        path.mkdir(parents=False)
        verified = path.is_dir()
        return self._success(action, f"Created folder: {path}", "Python pathlib", started) if verified else self._failure(action, "Folder creation could not be verified.", started)

    def _calculate(self, action: ActionRequest, started: float) -> ActionResult:
        expression = str(action.parameters.get("expression") or action.target)
        response = self.math_engine.solve(expression)
        if not response.get("ok"):
            message = (response.get("error") or {}).get("message") or "Calculation failed."
            return self._failure(action, str(message), started)
        data = response.get("data", {})
        result = data.get("result")
        expression = str(data.get("expression") or expression)
        return self._success(
            action,
            f"{expression} = {result}",
            "Python Math Engine",
            started,
            {"expression": expression, "result": result, "authoritative": True, "llm_used": False},
        )

    def _type_text(self, action: ActionRequest, started: float) -> ActionResult:
        text = str(action.parameters.get("text") or action.target)
        try:
            import pyautogui
        except ImportError:
            return self._failure(action, "Typing automation is unavailable because pyautogui is not installed.", started)
        pyautogui.write(text, interval=0.01)
        return self._success(action, f"Typed text.", "pyautogui", started, {"characters": len(text)})

    def _rename_file(self, action: ActionRequest, started: float) -> ActionResult:
        source = Path(action.target).expanduser()
        if not source.is_file():
            return self._failure(action, f"File not found: {source}", started)
        new_name = str(action.parameters.get("new_name", "")).strip()
        if not new_name or any(sep in new_name for sep in ("\\", "/")):
            return self._failure(action, "Invalid rename target.", started)
        destination = source.with_name(new_name)
        if destination.exists():
            return self._failure(action, f"Destination already exists: {destination}", started)
        source.rename(destination)
        return self._success(action, f"Renamed file to: {destination}", "Python pathlib", started, {"destination": str(destination)})

    def _copy_file(self, action: ActionRequest, started: float) -> ActionResult:
        source = Path(action.target).expanduser()
        destination = self._destination_for(source, str(action.parameters.get("destination", "")))
        if not source.is_file():
            return self._failure(action, f"File not found: {source}", started)
        if destination.exists():
            return self._failure(action, f"Destination already exists: {destination}", started)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return self._success(action, f"Copied file to: {destination}", "Python shutil", started, {"destination": str(destination)})

    def _move_file(self, action: ActionRequest, started: float) -> ActionResult:
        source = Path(action.target).expanduser()
        destination = self._destination_for(source, str(action.parameters.get("destination", "")))
        if not source.is_file():
            return self._failure(action, f"File not found: {source}", started)
        if destination.exists():
            return self._failure(action, f"Destination already exists: {destination}", started)
        if not destination.parent.exists():
            return self._failure(action, f"Destination folder does not exist: {destination.parent}", started)
        shutil.move(str(source), str(destination))
        return self._success(action, f"Moved file to: {destination}", "Python shutil", started, {"destination": str(destination)})

    @staticmethod
    def _destination_for(source: Path, requested: str) -> Path:
        destination = Path(requested).expanduser()
        if destination.exists() and destination.is_dir():
            return destination / source.name
        if requested.endswith(("\\", "/")):
            return destination / source.name
        return destination

    def _success(self, action: ActionRequest, message: str, source: str, started: float, metadata: dict | None = None) -> ActionResult:
        return ActionResult(True, action.action_id, action.action_type, message, source, action.target, round(time.perf_counter() - started, 3), metadata=metadata or {}, status=ActionExecutionStatus.SUCCESS.value)

    def _failure(self, action: ActionRequest, error: str, started: float, status: str = ActionExecutionStatus.FAILED.value) -> ActionResult:
        return ActionResult(False, action.action_id, action.action_type, error, "AURA HANDS Executor", action.target, round(time.perf_counter() - started, 3), error=error, status=status)

    def _not_implemented(self, action: ActionRequest, started: float) -> ActionResult:
        message = self._not_implemented_message(action)
        return ActionResult(
            False,
            action.action_id,
            action.action_type,
            message,
            "AURA HANDS Executor",
            action.target,
            round(time.perf_counter() - started, 3),
            error=message,
            metadata={"implemented": False},
            status=ActionExecutionStatus.NOT_IMPLEMENTED.value,
        )

    @staticmethod
    def _not_implemented_message(action: ActionRequest) -> str:
        if action.action_type == ActionType.PLAY_MEDIA:
            return f"{action.target} is targeted, but media playback control is not available yet."
        if action.action_type == ActionType.CLOSE_APPLICATION:
            return f"{action.target} is targeted, but closing applications is not available yet."
        if action.action_type == ActionType.FOCUS_APPLICATION:
            return f"{action.target} is targeted, but focusing applications is not available yet."
        return f"{action.action_type.value.replace('_', ' ')} is not available yet."
