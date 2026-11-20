"""
AURA Action Planner & Task Orchestrator
Translates natural-language user requests into structured, multi-step desktop workflows.
Performs typo tolerance, intent decomposition, sandbox permission validation, tool execution,
and state verification.
"""

from typing import Dict, Any, List, Optional, Tuple
import re
import difflib
import logging
from backend.services.tool_registry import tool_registry, ToolDefinition, RiskLevel
from backend.services.system_tool_service import SystemToolService
from backend.services.file_manager_service import FileManagerService
from backend.services.dev_assistant_service import DevAssistantService
from backend.security.sandbox import AuraSandboxProtocol
from backend.desktop import (
    desktop_controller,
    mouse_controller,
    keyboard_controller,
    window_manager,
    desktop_perception,
    browser_controller,
    media_controller,
    file_explorer_controller,
)
from backend.services.perception_cache import perception_cache
from backend.services.vision_service import VisionService
from backend.services.resource_monitor import resource_monitor

logger = logging.getLogger(__name__)


class ActionPlanner:
    """Intelligent action planning and multi-step task execution engine."""

    # Register built-in system tools into tool registry
    @classmethod
    def initialize_registry(cls) -> None:
        """Register all desktop, file, media, dev, and system tools."""
        # 1. Universal App Control & Window Management
        tool_registry.register(ToolDefinition(
            name="launch_app",
            description="Launch or foreground an installed Windows desktop application, game, or store app.",
            category="Application",
            risk_level=RiskLevel.LOW,
            parameters_schema={"app_key": "string"},
            execute=lambda app_key: SystemToolService.launch_app(app_key),
        ))
        tool_registry.register(ToolDefinition(
            name="close_app",
            description="Safely close an application window by sending WM_CLOSE.",
            category="Application",
            risk_level=RiskLevel.MEDIUM,
            parameters_schema={"app_key": "string"},
            execute=lambda app_key: SystemToolService.close_app(app_key),
        ))
        tool_registry.register(ToolDefinition(
            name="minimize_app",
            description="Minimize an active application window.",
            category="Window",
            risk_level=RiskLevel.LOW,
            parameters_schema={"app_key": "string"},
            execute=lambda app_key: SystemToolService.minimize_app(app_key),
        ))
        tool_registry.register(ToolDefinition(
            name="maximize_app",
            description="Maximize an application window to full screen.",
            category="Window",
            risk_level=RiskLevel.LOW,
            parameters_schema={"app_key": "string"},
            execute=lambda app_key: SystemToolService.maximize_app(app_key),
        ))
        tool_registry.register(ToolDefinition(
            name="get_active_window",
            description="Get information about the currently active foreground window.",
            category="Window",
            risk_level=RiskLevel.LOW,
            execute=lambda: SystemToolService.get_active_window(),
        ))
        tool_registry.register(ToolDefinition(
            name="list_running_apps",
            description="List active visible applications running on the user's desktop.",
            category="Window",
            risk_level=RiskLevel.LOW,
            execute=lambda: SystemToolService.list_running_apps(),
        ))

        # 2. Universal Web & Search
        tool_registry.register(ToolDefinition(
            name="search_youtube",
            description="Search YouTube or play video/audio in default browser.",
            category="Web",
            risk_level=RiskLevel.LOW,
            parameters_schema={"query": "string"},
            execute=lambda query: SystemToolService.search_youtube(query),
        ))
        tool_registry.register(ToolDefinition(
            name="search_google",
            description="Search Google in default browser.",
            category="Web",
            risk_level=RiskLevel.LOW,
            parameters_schema={"query": "string"},
            execute=lambda query: SystemToolService.search_google(query),
        ))

        # 3. File & Folder Management
        tool_registry.register(ToolDefinition(
            name="file_search",
            description="Search for files by name or extension in standard directories.",
            category="FileSystem",
            risk_level=RiskLevel.LOW,
            parameters_schema={"query": "string"},
            execute=lambda query: FileManagerService.search_files(query),
        ))
        tool_registry.register(ToolDefinition(
            name="organize_downloads",
            description="Organize Downloads folder into categorized folders with preview plan.",
            category="FileSystem",
            risk_level=RiskLevel.MEDIUM,
            parameters_schema={"preview": "bool"},
            execute=lambda preview=True: FileManagerService.organize_downloads(preview=preview),
        ))
        tool_registry.register(ToolDefinition(
            name="find_large_files",
            description="Find files larger than specified megabytes.",
            category="FileSystem",
            risk_level=RiskLevel.LOW,
            parameters_schema={"min_mb": "int"},
            execute=lambda min_mb=500: FileManagerService.find_large_files(min_mb=min_mb),
        ))
        tool_registry.register(ToolDefinition(
            name="find_duplicate_files",
            description="Detect duplicate files by MD5 checksum.",
            category="FileSystem",
            risk_level=RiskLevel.LOW,
            execute=lambda: FileManagerService.find_duplicate_files(),
        ))
        tool_registry.register(ToolDefinition(
            name="storage_drives",
            description="Inspect disk partition capacity and free space.",
            category="System",
            risk_level=RiskLevel.LOW,
            execute=lambda: FileManagerService.get_storage_drives(),
        ))
        tool_registry.register(ToolDefinition(
            name="read_document",
            description="Read and summarize document contents (PDF, DOCX, TXT, MD, CSV).",
            category="FileSystem",
            risk_level=RiskLevel.LOW,
            parameters_schema={"file_path": "string"},
            execute=lambda file_path: FileManagerService.read_document_summary(file_path),
        ))

        # 4. Entertainment & Media Control
        tool_registry.register(ToolDefinition(
            name="volume_up",
            description="Increase master audio volume.",
            category="Media",
            risk_level=RiskLevel.LOW,
            execute=lambda steps=5: SystemToolService.volume_up(steps),
        ))
        tool_registry.register(ToolDefinition(
            name="volume_down",
            description="Decrease master audio volume.",
            category="Media",
            risk_level=RiskLevel.LOW,
            execute=lambda steps=5: SystemToolService.volume_down(steps),
        ))
        tool_registry.register(ToolDefinition(
            name="volume_mute",
            description="Toggle master audio mute.",
            category="Media",
            risk_level=RiskLevel.LOW,
            execute=lambda: SystemToolService.volume_mute(),
        ))
        tool_registry.register(ToolDefinition(
            name="media_play_pause",
            description="Toggle media playback (play/pause).",
            category="Media",
            risk_level=RiskLevel.LOW,
            execute=lambda: {
                "handled": True,
                "action": "media_play_pause",
                "title": "Media Play / Pause",
                "message": "Media playback state toggled.",
                "spoken_response": "Toggled playback.",
                "data": media_controller.play_pause(),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="media_next",
            description="Skip to next media track.",
            category="Media",
            risk_level=RiskLevel.LOW,
            execute=lambda: {
                "handled": True,
                "action": "media_next",
                "title": "Next Track",
                "message": "Skipped to next track.",
                "spoken_response": "Playing next track.",
                "data": media_controller.next_track(),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="media_previous",
            description="Return to previous media track.",
            category="Media",
            risk_level=RiskLevel.LOW,
            execute=lambda: {
                "handled": True,
                "action": "media_previous",
                "title": "Previous Track",
                "message": "Returned to previous track.",
                "spoken_response": "Playing previous track.",
                "data": media_controller.previous_track(),
            },
        ))

        # 5. Developer Assistant
        tool_registry.register(ToolDefinition(
            name="git_status",
            description="Inspect Git branch and modified files in project.",
            category="Developer",
            risk_level=RiskLevel.LOW,
            execute=lambda: DevAssistantService.get_git_status(),
        ))
        tool_registry.register(ToolDefinition(
            name="git_diff",
            description="Inspect summarized Git diff of uncommitted changes.",
            category="Developer",
            risk_level=RiskLevel.LOW,
            execute=lambda: DevAssistantService.get_git_diff_summary(),
        ))
        tool_registry.register(ToolDefinition(
            name="run_unit_tests",
            description="Run approved Python project test suite in sandbox mode.",
            category="Developer",
            risk_level=RiskLevel.MEDIUM,
            execute=lambda: DevAssistantService.run_approved_unit_tests(),
        ))

        # 6. System Diagnostics
        tool_registry.register(ToolDefinition(
            name="battery_status",
            description="Retrieve battery charge percentage and power state.",
            category="System",
            risk_level=RiskLevel.LOW,
            execute=lambda: SystemToolService.get_system_battery(),
        ))
        tool_registry.register(ToolDefinition(
            name="hardware_specs",
            description="Inspect CPU and RAM utilization.",
            category="System",
            risk_level=RiskLevel.LOW,
            execute=lambda: SystemToolService.get_system_ram_cpu(),
        ))
        tool_registry.register(ToolDefinition(
            name="clipboard_inspect",
            description="Read and summarize current Windows clipboard text.",
            category="System",
            risk_level=RiskLevel.LOW,
            execute=lambda: SystemToolService.inspect_clipboard(),
        ))

        # 7. Desktop Automation & Direct Hardware Control
        tool_registry.register(ToolDefinition(
            name="desktop_mouse_move",
            description="Smoothly move mouse pointer to (x, y) coordinates with cubic bezier easing.",
            category="Desktop",
            risk_level=RiskLevel.LOW,
            parameters_schema={"x": "int", "y": "int", "smooth": "bool", "duration": "float"},
            execute=lambda x, y, smooth=True, duration=0.3: {
                "handled": True,
                "action": "mouse_move",
                "title": f"Moved Mouse to ({x}, {y})",
                "message": f"Mouse pointer navigated smoothly to ({x}, {y}).",
                "spoken_response": f"Mouse moved to {x}, {y}.",
                "data": {"success": mouse_controller.move_to(int(x), int(y), smooth=bool(smooth), duration=float(duration)), "x": x, "y": y},
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_mouse_click",
            description="Click mouse button at current or specified screen position.",
            category="Desktop",
            risk_level=RiskLevel.LOW,
            parameters_schema={"x": "int", "y": "int", "button": "string", "clicks": "int"},
            execute=lambda x=None, y=None, button="left", clicks=1: {
                "handled": True,
                "action": "mouse_click",
                "title": f"Mouse {button.capitalize()} Click",
                "message": f"Performed {clicks} {button} click(s).",
                "spoken_response": f"{button.capitalize()} clicked.",
                "data": {"success": mouse_controller.click(x=x, y=y, button=button, clicks=clicks), "button": button, "clicks": clicks},
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_mouse_scroll",
            description="Scroll mouse wheel vertically or horizontally.",
            category="Desktop",
            risk_level=RiskLevel.LOW,
            parameters_schema={"clicks": "int", "horizontal": "bool"},
            execute=lambda clicks=3, horizontal=False: {
                "handled": True,
                "action": "mouse_scroll",
                "title": "Mouse Scrolled",
                "message": f"Scrolled {'horizontally' if horizontal else 'vertically'} by {clicks} ticks.",
                "spoken_response": f"Scrolled {'down' if clicks > 0 else 'up'}.",
                "data": {"success": mouse_controller.scroll(clicks=int(clicks), horizontal=bool(horizontal))},
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_type_text",
            description="Type text into active foreground window using Win32 SendInput.",
            category="Desktop",
            risk_level=RiskLevel.LOW,
            parameters_schema={"text": "string"},
            execute=lambda text: {
                "handled": True,
                "action": "type_text",
                "title": "Typed Text",
                "message": f"Typed {len(text)} characters into focused window.",
                "spoken_response": "I have typed the text for you.",
                "data": {"success": keyboard_controller.type_text(text), "length": len(text)},
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_hotkey",
            description="Execute keyboard shortcut combination (e.g. Ctrl+C, Alt+Tab, Win+R).",
            category="Desktop",
            risk_level=RiskLevel.LOW,
            parameters_schema={"keys": "list or string"},
            execute=lambda keys: {
                "handled": True,
                "action": "keyboard_hotkey",
                "title": f"Hotkey: {'+'.join(keys) if isinstance(keys, (list, tuple)) else str(keys)}",
                "message": f"Sent keyboard shortcut: {'+'.join(keys) if isinstance(keys, (list, tuple)) else str(keys)}",
                "spoken_response": f"Pressed {' plus '.join(keys) if isinstance(keys, (list, tuple)) else str(keys)}.",
                "data": {
                    "success": keyboard_controller.hotkey(*(keys if isinstance(keys, (list, tuple)) else [str(keys)])),
                    "keys": list(keys) if isinstance(keys, (list, tuple)) else [str(keys)],
                },
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_open_app",
            description="Open or focus a Windows desktop application.",
            category="Desktop",
            risk_level=RiskLevel.LOW,
            parameters_schema={"app_name": "string"},
            execute=lambda app_name: {
                "handled": True,
                "action": "app_launch",
                "title": f"Launched {app_name.capitalize()}",
                "message": f"Opening {app_name.capitalize()} on your desktop.",
                "spoken_response": f"Opening {app_name}.",
                "data": desktop_controller.open_app(app_name),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_open_and_type",
            description="Launch or focus an application and type text into it.",
            category="Desktop",
            risk_level=RiskLevel.LOW,
            parameters_schema={"app_name": "string", "text": "string"},
            execute=lambda app_name, text: {
                "handled": True,
                "action": "open_and_type",
                "title": f"Type into {app_name.capitalize()}",
                "message": f"Opened {app_name.capitalize()} and entered text.",
                "spoken_response": f"I've opened {app_name} and typed your text.",
                "data": desktop_controller.open_and_type(app_name, text),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_browser_search",
            description="Open browser, move virtual hand to address bar, click, type search query, and press enter.",
            category="Desktop",
            risk_level=RiskLevel.LOW,
            parameters_schema={"browser": "string", "query": "string"},
            execute=lambda browser, query: {
                "handled": True,
                "action": "browser_search",
                "title": f"Searching on {browser.capitalize()}: {query}",
                "message": f"Opened {browser.capitalize()}, navigated address bar, and searched for '{query}'.",
                "spoken_response": f"Opening {browser} and searching for {query}.",
                "data": desktop_controller.browser_search(browser, query),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_media_search",
            description="Search Spotify or YouTube for music or video.",
            category="Media",
            risk_level=RiskLevel.LOW,
            parameters_schema={"query": "string", "platform": "string"},
            execute=lambda query, platform="spotify": {
                "handled": True,
                "action": "web_search" if platform.lower() in ("youtube", "yt") else "media_search",
                "title": f"YouTube: {query}" if platform.lower() in ("youtube", "yt") else f"Playing on {platform.capitalize()}: {query}",
                "message": f"Searched {platform.capitalize()} for '{query}'.",
                "spoken_response": f"Searching for {query} on {platform}.",
                "data": (
                    media_controller.search_spotify(query)
                    if platform.lower() == "spotify"
                    else media_controller.search_youtube(query)
                ),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_media_play",
            description="Play video, song or media on YouTube or Spotify.",
            category="Media",
            risk_level=RiskLevel.LOW,
            parameters_schema={"query": "string", "platform": "string"},
            execute=lambda query, platform="youtube": {
                "handled": True,
                "action": "media_play",
                "title": f"Playing on {platform.capitalize()}: {query}",
                "message": f"Playing '{query}' on {platform.capitalize()}.",
                "spoken_response": f"Playing {query} on {platform}.",
                "data": (
                    media_controller.play_spotify(query)
                    if platform.lower() == "spotify"
                    else media_controller.play_youtube(query)
                ),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_media_seek_relative",
            description="Seek forward or backward by seconds on active media player (YouTube or Spotify).",
            category="Media",
            risk_level=RiskLevel.LOW,
            parameters_schema={"seconds": "int"},
            execute=lambda seconds=10: {
                "handled": True,
                "action": "media_seek",
                "title": f"Seeked {'Forward' if int(seconds) > 0 else 'Backward'}",
                "message": f"Seeked {'forward' if int(seconds) > 0 else 'backward'} {abs(int(seconds))} seconds.",
                "spoken_response": f"Seeked {'forward' if int(seconds) > 0 else 'backward'} {abs(int(seconds))} seconds.",
                "data": media_controller.seek_relative(int(seconds)),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_media_seek_percent",
            description="Seek to percentage (0-100%) on active media player timeline scrubber.",
            category="Media",
            risk_level=RiskLevel.LOW,
            parameters_schema={"percent": "int"},
            execute=lambda percent=50: {
                "handled": True,
                "action": "media_seek",
                "title": f"Seeked to {int(percent)}%",
                "message": f"Seeked to {int(percent)}% on timeline scrubber.",
                "spoken_response": f"Seeked to {int(percent)} percent.",
                "data": media_controller.seek_percentage(int(percent)),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_media_seek_time",
            description="Seek to a specific timestamp (minutes and seconds).",
            category="Media",
            risk_level=RiskLevel.LOW,
            parameters_schema={"minutes": "int", "seconds": "int"},
            execute=lambda minutes=0, seconds=0: {
                "handled": True,
                "action": "media_seek",
                "title": f"Seeked to {int(minutes)}:{int(seconds):02d}",
                "message": f"Seeked to {int(minutes)} minutes {int(seconds)} seconds.",
                "spoken_response": f"Jumped to {int(minutes)} minutes {int(seconds)} seconds.",
                "data": media_controller.seek_to_time(int(minutes), int(seconds)),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_select_media_result",
            description="Select the N-th result from the previous media search.",
            category="Media",
            risk_level=RiskLevel.LOW,
            parameters_schema={"index": "int"},
            execute=lambda index=1: {
                "handled": True,
                "action": "media_select_result",
                "title": f"Selected Result #{index}",
                "message": f"Selected result #{index} from recent media search.",
                "spoken_response": f"Playing result number {index}.",
                "data": media_controller.select_result(int(index)),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_open_folder",
            description="Open Windows File Explorer to a specified directory (Downloads, Documents, Desktop, etc.).",
            category="FileSystem",
            risk_level=RiskLevel.LOW,
            parameters_schema={"folder": "string"},
            execute=lambda folder="downloads": {
                "handled": True,
                "action": "open_folder",
                "title": f"Opened Folder: {folder.capitalize()}",
                "message": f"Opened {folder.capitalize()} folder in File Explorer.",
                "spoken_response": f"Opening {folder} folder.",
                "data": file_explorer_controller.open_folder(folder),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="desktop_browser_tab",
            description="Manage browser tabs (new_tab, close_tab, reopen_tab, next_tab, previous_tab).",
            category="Browser",
            risk_level=RiskLevel.LOW,
            parameters_schema={"action": "string"},
            execute=lambda action="new_tab": {
                "handled": True,
                "action": f"browser_{action}",
                "title": f"Browser: {action.replace('_', ' ').title()}",
                "message": f"Executed browser action: {action}",
                "spoken_response": f"Browser {action.replace('_', ' ')}.",
                "data": getattr(browser_controller, action, browser_controller.new_tab)(),
            },
        ))

        # 8. Resource Management & Cache Telemetry
        tool_registry.register(ToolDefinition(
            name="perception_cache_clear",
            description="Clear cached screen OCR and vision perception data and force memory garbage collection.",
            category="System",
            risk_level=RiskLevel.LOW,
            execute=lambda: {
                "handled": True,
                "action": "cache_cleared",
                "title": "Perception Cache Cleared",
                "message": f"Evicted {perception_cache.invalidate_all('User command')} entries from perception cache. Garbage collection completed.",
                "spoken_response": "Perception cache has been cleared and memory released.",
                "data": perception_cache.get_stats(),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="unload_gpu_models",
            description="Unload idle vision/LLM models from GPU VRAM and purge CUDA memory cache.",
            category="System",
            risk_level=RiskLevel.LOW,
            execute=lambda: {
                "handled": True,
                "action": "gpu_unloaded",
                "title": "GPU Models Unloaded",
                "message": "Released models from GPU VRAM and cleared PyTorch CUDA cache.",
                "spoken_response": "GPU resources and vision models have been released from VRAM.",
                "data": VisionService.unload_vision_models(),
            },
        ))
        tool_registry.register(ToolDefinition(
            name="get_resource_metrics",
            description="Inspect system RAM, GPU VRAM, CPU utilization, and perception latency.",
            category="System",
            risk_level=RiskLevel.LOW,
            execute=lambda: {
                "handled": True,
                "action": "resource_metrics",
                "title": "System Resource Telemetry",
                "message": f"RAM: {resource_monitor.get_metrics()['ram']['process_mb']} MB (Process) | GPU VRAM: {resource_monitor.get_metrics()['gpu']['allocated_mb']} MB allocated | CPU: {resource_monitor.get_metrics()['cpu']['system_percent']}%",
                "spoken_response": f"System RAM is at {resource_monitor.get_metrics()['ram']['system_percent']} percent, with {resource_monitor.get_metrics()['ram']['process_mb']} megabytes used by AURA.",
                "data": resource_monitor.get_metrics(),
            },
        ))

        # 9. Screen Perception & Fast In-Memory OCR
        tool_registry.register(ToolDefinition(
            name="screen_read_text",
            description="Read all visible text on the active desktop screen using zero-VRAM Windows Media OCR.",
            category="Perception",
            risk_level=RiskLevel.LOW,
            parameters_schema={"prompt": "string"},
            execute=lambda prompt="Read text on screen": SystemToolService.capture_and_analyze_screen(prompt),
        ))

        # Email & Reminders Tools (Phase V1 Email Notifications)
        from backend.services.email_service import email_service
        from backend.services.important_notes_service import important_notes_service
        from backend.services.daily_summary_service import daily_summary_service

        tool_registry.register(ToolDefinition(
            name="send_test_email",
            description="Send a test email notification to verify Gmail integration.",
            category="Email",
            risk_level=RiskLevel.LOW,
            parameters_schema={"to_email": "string (optional)"},
            execute=lambda to_email=None: email_service.send_test_email(to_email=to_email),
        ))
        tool_registry.register(ToolDefinition(
            name="send_email_notification",
            description="Send an email notification or reminder to the configured destination address.",
            category="Email",
            risk_level=RiskLevel.LOW,
            parameters_schema={"subject": "string", "body": "string", "to_email": "string (optional)"},
            execute=lambda subject, body, to_email=None: email_service.send_email(to_email=to_email, subject=subject, body_text=body),
        ))
        tool_registry.register(ToolDefinition(
            name="save_important_note",
            description="Save key information, reminders, or deadlines as an important note in SQLite.",
            category="Email",
            risk_level=RiskLevel.LOW,
            parameters_schema={"content": "string", "email_now": "boolean (optional)"},
            execute=lambda content, email_now=False: important_notes_service.add_note(content=content, emailed=email_now),
        ))
        tool_registry.register(ToolDefinition(
            name="send_daily_summary",
            description="Compile and dispatch the morning daily summary digest email.",
            category="Email",
            risk_level=RiskLevel.LOW,
            parameters_schema={"to_email": "string (optional)"},
            execute=lambda to_email=None: daily_summary_service.send_summary_now(to_email=to_email),
        ))

    @classmethod
    def plan_and_execute(cls, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Decomposes user instruction into an action plan.
        Supports single actions, compound multi-step workflows, and typo-tolerant queries.
        Returns result payload if handled, else None.
        """
        from backend.services.system_tool_service import ensure_interactive_desktop
        ensure_interactive_desktop()

        p = prompt.strip().lower()

        # Step 0: Check for compound commands joined by " and "
        # E.g. "open spotify and check my battery", "close notepad and check git status"
        compound_match = re.match(r"^(.+?)\s+and\s+(.+)$", p)
        if compound_match:
            part1 = compound_match.group(1).strip()
            part2 = compound_match.group(2).strip()

            # Disqualify if part1 is "search for X" or if command is "open X and type Y", "open X and search Y", "open X and play Y"
            if not any(part1.startswith(s) for s in ("search", "find", "google", "explain", "who is", "what is")) and not any(part2.startswith(s) for s in ("type ", "search ", "search", "play ", "play")):
                res1 = cls._dispatch_single_action(part1)
                res2 = cls._dispatch_single_action(part2)
                if res1 and res2:
                    # Multi-step composite workflow executed!
                    spoken = f"{res1.get('spoken_response', '')} Also, {res2.get('spoken_response', '')}".strip()
                    return {
                        "handled": True,
                        "action": "composite_workflow",
                        "title": "Completed Multi-Step Workflow",
                        "message": f"1. {res1.get('message', '')}\n2. {res2.get('message', '')}",
                        "spoken_response": spoken,
                        "data": {
                            "step_count": 2,
                            "steps": [res1, res2],
                        },
                    }

        # Step 1: Dispatch single action
        return cls._dispatch_single_action(prompt)

    @classmethod
    def _dispatch_single_action(cls, prompt: str) -> Optional[Dict[str, Any]]:
        """Intelligent single-action matcher and executor."""
        p = prompt.strip().lower()

        # 1. Window Management (Minimize, Maximize, Close, Active, Running Apps)
        min_m = re.search(r"^(?:please\s+)?(?:can you\s+)?(?:minimize)\s+([a-zA-Z0-9\s]+?)(?:\s+window|\s+app)?$", p)
        if min_m:
            return tool_registry.execute("minimize_app", app_key=min_m.group(1).strip())

        max_m = re.search(r"^(?:please\s+)?(?:can you\s+)?(?:maximize)\s+([a-zA-Z0-9\s]+?)(?:\s+window|\s+app)?$", p)
        if max_m:
            return tool_registry.execute("maximize_app", app_key=max_m.group(1).strip())

        close_m = re.search(r"^(?:please\s+)?(?:can you\s+)?(?:close|quit|exit)\s+([a-zA-Z0-9\s]+?)(?:\s+window|\s+app)?$", p)
        if close_m:
            cand = close_m.group(1).strip()
            if cand not in ("browser", "tab", "my window"):
                return tool_registry.execute("close_app", app_key=cand)

        if re.search(r"\b(what(?:'s|\s+is)\s+the\s+active\s+window|active\s+window|current\s+window|what\s+app\s+am\s+i\s+using|what\s+is\s+open)\b", p):
            return tool_registry.execute("get_active_window")

        if re.search(r"\b(list\s+(?:open|running)\s+apps|what\s+apps\s+are\s+running|show\s+running\s+applications)\b", p):
            return tool_registry.execute("list_running_apps")

        # 2. File & Storage Tools
        if re.search(r"\b(organize\s+(?:my\s+)?downloads(?:\s+folder)?|clean\s+up\s+(?:my\s+)?downloads)\b", p):
            return tool_registry.execute("organize_downloads", preview=True)

        if re.search(r"\b(find\s+duplicate\s+files|duplicate\s+files|check\s+duplicates)\b", p):
            return tool_registry.execute("find_duplicate_files")

        if re.search(r"\b(find\s+large\s+files|large\s+files|files\s+larger\s+than)\b", p):
            return tool_registry.execute("find_large_files", min_mb=500)

        if re.search(r"\b(storage\s+usage|disk\s+space|how\s+much\s+(?:free\s+)?storage|storage\s+drives)\b", p):
            return tool_registry.execute("storage_drives")

        file_search_m = re.search(r"\b(?:find\s+(?:file|files?)|search\s+for\s+(?:file|document))\s+(.+)$", p)
        if file_search_m:
            return tool_registry.execute("file_search", query=file_search_m.group(1).strip())

        # 3. Developer Assistant Tools
        if re.search(r"\b(git\s+status|check\s+git\s+changes|show\s+git\s+status)\b", p):
            return tool_registry.execute("git_status")

        if re.search(r"\b(git\s+diff|show\s+code\s+diff|uncommitted\s+changes)\b", p):
            return tool_registry.execute("git_diff")

        if re.search(r"\b(run\s+(?:project\s+)?(?:unit\s+)?tests|test\s+the\s+project|execute\s+tests)\b", p):
            return tool_registry.execute("run_unit_tests")

        # 4. Desktop Direct Hardware Automation (Mouse, Keyboard, Open & Type, Spotify, Explorer, Tabs)
        # 4a. Open app and type / Type into app (preserve exact case of typed text)
        open_type_m = re.match(
            r"^(?:please\s+)?(?:can you\s+)?(?:open(?:\s+up)?|launch|start)\s+([a-zA-Z0-9\s]+?)\s+and\s+type\s+(.+)$",
            prompt.strip(),
            re.IGNORECASE,
        )
        if open_type_m:
            app_target = open_type_m.group(1).strip()
            text_to_type = open_type_m.group(2).strip()
            return tool_registry.execute("desktop_open_and_type", app_name=app_target, text=text_to_type)

        type_into_m = re.match(
            r"^(?:please\s+)?(?:can you\s+)?type\s+(.+?)\s+into\s+([a-zA-Z0-9\s]+)$",
            prompt.strip(),
            re.IGNORECASE,
        )
        if type_into_m:
            text_to_type = type_into_m.group(1).strip()
            app_target = type_into_m.group(2).strip()
            return tool_registry.execute("desktop_open_and_type", app_name=app_target, text=text_to_type)

        # Standalone typing (preserve exact case)
        just_type_m = re.match(r"^(?:please\s+)?(?:can you\s+)?(?:type|type:\s*)\s+(.+)$", prompt.strip(), re.IGNORECASE)
        if just_type_m and not just_type_m.group(1).lower().startswith("into "):
            return tool_registry.execute("desktop_type_text", text=just_type_m.group(1).strip())

        # 4b. Spotify Play & Search intents
        # Handles: "open spotify and play <query>", "play <query> on spotify", "spotify play <query>",
        #          "open spotify and search <query>", "search <query> on spotify", "spotify search <query>"
        spotify_play_m = re.search(
            r"\b(?:open\s+(?:the\s+)?spotify\s+(?:and\s+)?play\s+(.+)|play\s+(.+?)\s+(?:in|on)\s+spotify|spotify\s+play\s+(.+)|search\s+(.+?)\s+(?:in|on)\s+spotify\s+and\s+play)\b",
            prompt.strip(),
            re.IGNORECASE,
        )
        if spotify_play_m:
            song_q = (spotify_play_m.group(1) or spotify_play_m.group(2) or spotify_play_m.group(3) or spotify_play_m.group(4) or "").strip()
            clean_song = re.sub(r"\b(song|video|track|music|album|please)\b", "", song_q, flags=re.IGNORECASE).strip() or song_q.strip()
            return tool_registry.execute("desktop_media_play", query=clean_song, platform="spotify")

        spotify_search_m = re.search(
            r"\b(?:open\s+(?:the\s+)?spotify\s+(?:and\s+)?search(?:\s+for)?\s+(.+)|search\s+(.+?)\s+(?:in|on)\s+spotify|spotify\s+search(?:\s+for)?\s+(.+)|search\s+spotify\s+for\s+(.+))\b",
            prompt.strip(),
            re.IGNORECASE,
        )
        if spotify_search_m:
            search_q = (spotify_search_m.group(1) or spotify_search_m.group(2) or spotify_search_m.group(3) or spotify_search_m.group(4) or "").strip()
            return tool_registry.execute("desktop_media_search", query=search_q, platform="spotify")

        # 4b-1. YouTube Play intent ("play <query> in/on yt/youtube", "open yt and play <query>", etc.)
        yt_play_m = re.search(
            r"\b(?:play\s+(.+?)\s+(?:in|on)\s+(?:yt|youtube|u\s*tube|you\s*tube)|open\s+(?:the\s+)?(?:yt|youtube|u\s*tube|you\s*tube)\s+and\s+play\s+(.+)|play\s+(?:on\s+|in\s+)?(?:yt|youtube)\s+(.+))\b",
            prompt.strip(),
            re.IGNORECASE,
        )
        if yt_play_m:
            song_q = (yt_play_m.group(1) or yt_play_m.group(2) or yt_play_m.group(3) or "").strip()
            clean_song = re.sub(r"\b(song|video|track|music|please)\b", "", song_q, flags=re.IGNORECASE).strip() or song_q.strip()
            return tool_registry.execute("desktop_media_play", query=clean_song, platform="youtube")

        # 4b-2. YouTube Search intent ("open yt and search <query>", "search <query> on/in yt/youtube", etc.)
        yt_search_m = re.search(
            r"\b(?:open\s+(?:the\s+)?(?:yt|youtube|u\s*tube|you\s*tube)\s+and\s+search(?:\s+for)?\s+(.+)|search\s+(.+?)\s+(?:in|on)\s+(?:yt|youtube|u\s*tube|you\s*tube)|search\s+(?:on\s+|in\s+)?(?:yt|youtube|u\s*tube|you\s*tube)\s+(?:for\s+)?(.+)|(?:yt|youtube)\s+search(?:\s+for)?\s+(.+))\b",
            prompt.strip(),
            re.IGNORECASE,
        )
        if yt_search_m:
            search_q = (yt_search_m.group(1) or yt_search_m.group(2) or yt_search_m.group(3) or yt_search_m.group(4) or "").strip()
            return tool_registry.execute("desktop_media_search", query=search_q, platform="youtube")

        # 4b-3. Browser Search & Google Search intent
        # Handles: "search python tutorials on google", "search for python tutorials in google",
        #          "open chrome and search for python tutorials", "google python tutorials",
        #          "google search python tutorials", "search google for python tutorials"
        browser_search_m = re.search(
            r"\b(?:open|launch|start)\s+(chrome|edge|firefox|brave|browser|google)\s+and\s+search(?:\s+for)?\s+(.+)$",
            prompt.strip(),
            re.IGNORECASE,
        ) or re.search(
            r"\bsearch\s+(?:for\s+)?(.+?)\s+(?:on|in|using)\s+(chrome|edge|firefox|brave|browser|google)\b",
            prompt.strip(),
            re.IGNORECASE,
        ) or re.search(
            r"\b(?:google\s+search\s+(?:for\s+)?|search\s+google\s+(?:for\s+)?|google\s+)(.+)$",
            prompt.strip(),
            re.IGNORECASE,
        )
        if browser_search_m:
            if len(browser_search_m.groups()) == 1 or not browser_search_m.group(2):
                b_name = "chrome"
                b_query = (browser_search_m.group(1) or "").strip()
            else:
                g1 = (browser_search_m.group(1) or "").strip()
                g2 = (browser_search_m.group(2) or "").strip()
                if g1.lower() in ("chrome", "edge", "firefox", "brave", "browser", "google"):
                    b_name, b_query = g1, g2
                else:
                    b_name, b_query = g2, g1

            if b_name.lower() in ("google", "browser"):
                b_name = "chrome"

            # Filter out non-search conversational prompts like "google what is python"
            if b_name and b_query and not b_query.lower().startswith("what is your") and not b_query.lower().startswith("who are you"):
                return tool_registry.execute("desktop_browser_search", browser=b_name, query=b_query)

        # 4c. Timeline Scrubber & Seeking Controls (YouTube & Spotify)
        # Relative forward/backward seek: e.g. "forward 10 seconds", "skip 10s", "rewind 10 seconds", "go back 5s"
        seek_fwd_m = re.search(
            r"\b(?:forward|fast\s+forward|skip\s+forward|go\s+forward)\s+(?:by\s+)?(\d+)\s*(?:s|sec|secs|seconds)?\b",
            p,
        )
        if seek_fwd_m:
            return tool_registry.execute("desktop_media_seek_relative", seconds=int(seek_fwd_m.group(1)))

        seek_back_m = re.search(
            r"\b(?:rewind|backward|back|go\s+back|skip\s+backward|skip\s+back)\s+(?:by\s+)?(\d+)\s*(?:s|sec|secs|seconds)?\b",
            p,
        )
        if seek_back_m:
            return tool_registry.execute("desktop_media_seek_relative", seconds=-int(seek_back_m.group(1)))

        if re.search(r"^(?:fast\s+forward|skip\s+forward)$", p):
            return tool_registry.execute("desktop_media_seek_relative", seconds=10)
        if re.search(r"^(?:rewind|go\s+back)$", p):
            return tool_registry.execute("desktop_media_seek_relative", seconds=-10)

        # Percentage seek: e.g. "seek to 50%", "go to 50%", "go to middle", "restart"
        seek_pct_m = re.search(r"\b(?:seek|go|jump|scrub)\s+(?:to\s+)?(\d{1,3})\s*(?:%|\bpercent\b)", p)
        if seek_pct_m:
            return tool_registry.execute("desktop_media_seek_percent", percent=int(seek_pct_m.group(1)))

        if re.search(r"\b(?:go\s+to|seek\s+to)\s+(?:the\s+)?(?:middle|half)\b", p):
            return tool_registry.execute("desktop_media_seek_percent", percent=50)

        if re.search(r"^(?:restart|restart\s+video|restart\s+song|seek\s+to\s+start|go\s+to\s+beginning|from\s+the\s+start)$", p):
            return tool_registry.execute("desktop_media_seek_percent", percent=0)

        # Time seek: e.g. "go to 2:30", "go to 1 minute 30 seconds"
        seek_time_m = re.search(r"\b(?:go\s+to|jump\s+to|seek\s+to)\s+(\d{1,2}):(\d{2})\b", p)
        if seek_time_m:
            return tool_registry.execute(
                "desktop_media_seek_time",
                minutes=int(seek_time_m.group(1)),
                seconds=int(seek_time_m.group(2)),
            )

        seek_min_m = re.search(r"\b(?:go\s+to|jump\s+to|seek\s+to)\s+(\d+)\s+min(?:ute)?s?(?:\s+(?:and\s+)?(\d+)\s+sec(?:ond)?s?)?\b", p)
        if seek_min_m:
            return tool_registry.execute(
                "desktop_media_seek_time",
                minutes=int(seek_min_m.group(1)),
                seconds=int(seek_min_m.group(2) or 0),
            )

        # 4d. Media Next & Previous track
        if re.search(r"^(?:please\s+)?(?:can you\s+)?(?:next\s+song|next\s+track|next\s+video|next|skip\s+song|skip\s+track|skip)$", p):
            return tool_registry.execute("media_next")
        if re.search(r"^(?:please\s+)?(?:can you\s+)?(?:previous\s+song|previous\s+track|previous\s+video|previous|prev\s+song|prev\s+track|prev|replay\s+song|last\s+song)$", p):
            return tool_registry.execute("media_previous")

        # 4e. Media Play/Pause/Resume intent (CRITICAL FIX FOR "PLAY IT", "play", "pause", "resume")
        if re.search(
            r"^(?:please\s+)?(?:can you\s+)?(?:play\s+it|resume\s+it|resume|play\s+pause|toggle\s+play|pause\s+playback|play\s+playback|pause|stop\s+playback|stop\s+playing)$",
            p,
        ):
            return tool_registry.execute("media_play_pause")

        # 4f. Follow-up media result selection
        sel_m = re.search(
            r"\b(?:play|select|choose|open|click)\s+(?:the\s+)?(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|\d+)(?:\s+(?:result|song|track|video|item))?\b",
            p,
        )
        if sel_m and media_controller.last_media_context is not None:
            raw_ord = sel_m.group(1).strip().lower()
            ord_map = {
                "first": 1, "1st": 1, "one": 1, "1": 1,
                "second": 2, "2nd": 2, "two": 2, "2": 2,
                "third": 3, "3rd": 3, "three": 3, "3": 3,
                "fourth": 4, "4th": 4, "four": 4, "4": 4,
                "fifth": 5, "5th": 5, "five": 5, "5": 5,
            }
            idx = ord_map.get(raw_ord) or (int(raw_ord) if raw_ord.isdigit() else 1)
            return tool_registry.execute("desktop_select_media_result", index=idx)

        # 4g. Generic Play Intent ("play senjudare song", "play starboy", etc.)
        general_play_m = re.match(
            r"^(?:please\s+)?(?:can you\s+)?play\s+(.+?)(?:\s+song|\s+music|\s+video|\s+track)?$",
            prompt.strip(),
            re.IGNORECASE,
        )
        if general_play_m:
            target_media = general_play_m.group(1).strip()
            # Guard: never treat generic playback controls as a song query!
            if target_media.lower() in ("it", "this", "music", "song", "video", "track", "audio", "playback", "the song", "the video", "the music", "again"):
                return tool_registry.execute("media_play_pause")
            if not any(skip in target_media.lower() for skip in ("game", "with", "around", "next", "previous", "pause")):
                return tool_registry.execute("desktop_media_play", query=target_media, platform="youtube")

        # 4d. Keyboard Hotkeys (Ctrl+Shift+Esc, Alt+Tab, Win+R, Ctrl+C, Ctrl+V, etc.)
        hotkey_m = re.search(
            r"\b(?:press|hit|send|hotkey)\s+(ctrl\+[a-z0-9\+]+|alt\+[a-z0-9\+]+|win\+[a-z0-9\+]+|shift\+[a-z0-9\+]+|ctrl\s+[a-z0-9]|alt\s+[a-z0-9]|win\s+[a-z0-9]|escape|enter|tab|backspace|space)\b",
            p,
        )
        if hotkey_m:
            raw_combo = hotkey_m.group(1).strip()
            if "+" in raw_combo:
                keys = [k.strip() for k in raw_combo.split("+")]
            else:
                keys = raw_combo.split()
            return tool_registry.execute("desktop_hotkey", keys=keys)

        # 4e. Open folder / File Explorer
        folder_m = re.search(
            r"\b(?:open|show|explore)\s+(?:my\s+)?(downloads|documents|desktop|pictures|videos|music|file\s+explorer|files)(?:\s+folder)?\b",
            p,
        )
        if folder_m:
            f_target = folder_m.group(1).strip()
            return tool_registry.execute("desktop_open_folder", folder=f_target)

        # 4f. Browser Tab Controls
        if re.search(r"\b(new\s+tab|open\s+(?:a\s+)?new\s+tab)\b", p):
            return tool_registry.execute("desktop_browser_tab", action="new_tab")
        if re.search(r"\b(close\s+tab|close\s+current\s+tab)\b", p):
            return tool_registry.execute("desktop_browser_tab", action="close_tab")
        if re.search(r"\b(reopen\s+tab|reopen\s+closed\s+tab)\b", p):
            return tool_registry.execute("desktop_browser_tab", action="reopen_tab")
        if re.search(r"\b(next\s+tab|switch\s+to\s+next\s+tab)\b", p):
            return tool_registry.execute("desktop_browser_tab", action="next_tab")
        if re.search(r"\b(previous\s+tab|switch\s+to\s+prev(?:ious)?\s+tab)\b", p):
            return tool_registry.execute("desktop_browser_tab", action="previous_tab")

        # 4g. Mouse Coordinates & Navigation
        move_m = re.search(r"\b(?:move\s+mouse\s+(?:to\s+)?|move\s+cursor\s+(?:to\s+)?)(\d+)[,\s]+(\d+)\b", p)
        if move_m:
            x, y = int(move_m.group(1)), int(move_m.group(2))
            return tool_registry.execute("desktop_mouse_move", x=x, y=y)

        click_m = re.search(r"\bclick(?:\s+at)?\s+(\d+)[,\s]+(\d+)\b", p)
        if click_m:
            x, y = int(click_m.group(1)), int(click_m.group(2))
            return tool_registry.execute("desktop_mouse_click", x=x, y=y)

        if re.search(r"\b(right\s+click|context\s+menu)\b", p):
            return tool_registry.execute("desktop_mouse_click", button="right")

        if re.search(r"\b(double\s+click)\b", p):
            return tool_registry.execute("desktop_mouse_click", clicks=2)

        if re.search(r"\b(scroll\s+down)\b", p):
            return tool_registry.execute("desktop_mouse_scroll", clicks=3)

        if re.search(r"\b(scroll\s+up)\b", p):
            return tool_registry.execute("desktop_mouse_scroll", clicks=-3)

        # 4h. Resource & Perception Cache Management
        if re.search(r"\b(clear\s+(?:the\s+)?(?:perception\s+)?cache|flush\s+cache|free\s+up\s+memory|clean\s+(?:up\s+)?memory)\b", p):
            return tool_registry.execute("perception_cache_clear")

        if re.search(r"\b(unload\s+(?:gpu\s+)?models?|free\s+(?:gpu\s+)?vram|release\s+(?:gpu\s+)?vram)\b", p):
            return tool_registry.execute("unload_gpu_models")

        if re.search(r"\b(system\s+resources?|resource\s+metrics?|gpu\s+usage|vram\s+usage|memory\s+metrics?)\b", p):
            return tool_registry.execute("get_resource_metrics")

        # 4i. Screen Perception & Fast In-Memory OCR
        if re.search(r"\b(read\s+(?:the\s+)?(?:text|words?|content)?\s*(?:on\s+)?(?:my\s+)?screen|what(?:'s|\s+is)\s+(?:written|text)\s+(?:on\s+)?(?:my\s+)?screen|ocr\s+(?:my\s+)?screen|look\s+at\s+(?:my\s+)?screen)\b", p):
            return tool_registry.execute("screen_read_text", prompt=prompt)

        # 5. Fall back to standard SystemToolService intents (App launcher, YouTube search, volume, battery, clipboard)
        return SystemToolService.execute_intent(prompt)


# Initialize tools at module load
ActionPlanner.initialize_registry()
