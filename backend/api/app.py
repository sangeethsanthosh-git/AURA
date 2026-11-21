"""
FastAPI WebSocket backend for AURA Voice Assistant.
Phase 6: Streaming LLM -> Sentence-Chunked Piper PCM Synthesis -> Continuous Audio Playback.
"""

from pathlib import Path
import sys
import re
import time
import queue
import asyncio
import json
import logging
import threading
import base64
from typing import Set, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import (
    OLLAMA_MODEL,
    WAKE_WORD_PHRASE,
    AUDIO_SAMPLE_RATE,
    INPUT_SAMPLE_RATE,
    SILENCE_ENERGY_THRESHOLD,
    SILENCE_DURATION_SECONDS,
    MAX_RECORDING_DURATION,
    WIKIPEDIA_ENABLED_DEFAULT,
)
from backend.services.ollama_service import OllamaService
from backend.services.tts_service import TTSService
from backend.services.audio_service import AudioService
from backend.services.stt_service import STTService
from backend.services.wake_word_service import WakeWordService
from backend.services.wikipedia_service import WikipediaService
from backend.services.system_tool_service import SystemToolService
from backend.services.action_planner import ActionPlanner
from backend.services.vision_service import VisionService
from backend.services.rag_service import RAGService
from backend.services.reminder_service import ReminderService
from backend.services.email_service import email_service
from backend.services.important_notes_service import important_notes_service
from backend.services.daily_summary_service import daily_summary_service
from backend.security import (
    AuraSandboxProtocol,
    audit_logger,
    permission_gateway,
    process_sandbox,
    filesystem_guard,
    network_guard,
    prompt_guard,
    secret_store,
    emergency_stop,
)
from backend.services.cursor_service import windows_cursor_service
from backend.services.virtual_hand_theme_service import virtual_hand_theme_service
from backend.desktop.virtual_hand_controller import virtual_hand_controller
from backend.services.perception_cache import perception_cache
from backend.services.ocr_service import ocr_service
from backend.services.personality_service import personality_service, PersonalityProfile
from backend.services.resource_monitor import resource_monitor
from backend.desktop import desktop_controller
from backend.conversation.storage import ConversationStorage

logger = logging.getLogger("AURA.API")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AURA Voice Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Services
ollama_service = OllamaService()
tts_service = TTSService()
audio_service = AudioService()
stt_service = STTService()
wiki_service = WikipediaService()
vision_service = VisionService()
rag_service = RAGService()
reminder_service = ReminderService()
system_tool_service = SystemToolService()
system_tool_service.set_services(vision=vision_service, rag=rag_service, reminder=reminder_service)
storage = ConversationStorage()

# State & Task Management
CURRENT_STATE = "IDLE"  # IDLE, LISTENING, THINKING, SPEAKING, ERROR
active_connections: Set[WebSocket] = set()
current_pipeline_task: Optional[asyncio.Task] = None
current_cancel_event: Optional[threading.Event] = None
current_session_id: int = storage.get_latest_session_id()
deep_search_active: bool = (
    storage.get_setting("deep_search", "true" if WIKIPEDIA_ENABLED_DEFAULT else "false") == "true"
)
main_event_loop: Optional[asyncio.AbstractEventLoop] = None
timer_scheduler_task: Optional[asyncio.Task] = None

# Incremental sentence and early clause split regexes for low-latency streaming TTS
_FIRST_CLAUSE_SPLIT_RE = re.compile(r"[,;:.!?—\n]+(?=\s|\n|$)")
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?=\s|\n|$)|\n+")
_LONG_CLAUSE_SPLIT_RE = re.compile(r"[,;—]+(?=\s|\n|$)")


async def broadcast(message: dict) -> None:
    """Broadcast JSON message to all connected WebSocket clients."""
    for connection in list(active_connections):
        try:
            await connection.send_text(json.dumps(message))
        except Exception:
            active_connections.discard(connection)


async def set_state(new_state: str) -> None:
    """Update global state and notify all clients."""
    global CURRENT_STATE
    if emergency_stop.is_stopped() and new_state not in ("IDLE", "ERROR"):
        logger.warning(f"Rejecting state transition to {new_state} because Emergency Stop is active.")
        return
    CURRENT_STATE = new_state
    await broadcast({"type": "state_change", "state": new_state})


def on_wake_word_detected() -> None:
    """Callback fired by background WakeWordService when 'AURA' is heard."""
    logger.info("Wake-word 'AURA' detected! Triggering voice pipeline...")
    if main_event_loop and main_event_loop.is_running():
        asyncio.run_coroutine_threadsafe(_handle_wake_word_trigger(), main_event_loop)


async def _handle_wake_word_trigger() -> None:
    global current_pipeline_task
    # Voice interruption: If speaking or thinking, cancel previous playback/pipeline
    if CURRENT_STATE in ("SPEAKING", "THINKING"):
        cancel_current_pipeline()
    if CURRENT_STATE in ("IDLE", "SPEAKING", "THINKING"):
        await broadcast({"type": "wake_word_triggered", "phrase": WAKE_WORD_PHRASE})
        current_pipeline_task = asyncio.create_task(run_voice_pipeline())


# Initialize WakeWordService with loopback prevention
wake_word_service = WakeWordService(
    audio_service=audio_service,
    stt_service=stt_service,
    on_wake_detected=on_wake_word_detected,
)


async def _timer_scheduler_loop() -> None:
    """Periodic 1Hz timer check loop for reminders & desktop notifications."""
    logger.info("Timer & Reminder background scheduler loop active.")
    while True:
        try:
            expired = reminder_service.check_and_complete_expired()
            for r in expired:
                title = r.get("title", "Timer")
                rid = r.get("id")
                dur = r.get("duration_seconds", 0)
                logger.info(f"Timer #{rid} '{title}' expired! Firing notification.")
                # Native Windows Toast
                reminder_service.send_windows_toast(
                    "AURA: Timer Finished",
                    f"{title} is up!",
                )
                # Play audible earcon
                await asyncio.to_thread(audio_service.play_listening_chime, True)
                # Broadcast WebSocket event
                await broadcast({
                    "type": "timer_expired",
                    "id": rid,
                    "title": title,
                    "duration_seconds": dur,
                })
                # Spoken announcement
                spoken = f"Your timer for {title} is complete."
                storage.add_message(current_session_id, "assistant", spoken)
                await broadcast({"type": "response", "text": spoken})
                await _speak_tool_response(spoken, None)

            # Check scheduled daily summary digest (e.g. at 08:00)
            await asyncio.to_thread(daily_summary_service.check_and_send_daily_summary)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"Error in timer scheduler loop: {exc}")
        await asyncio.sleep(1.0)


@app.on_event("startup")
async def startup_event():
    global main_event_loop, timer_scheduler_task
    main_event_loop = asyncio.get_running_loop()
    virtual_hand_controller.set_event_loop(main_event_loop)
    emergency_stop.register_pipeline_canceller(cancel_current_pipeline)
    emergency_stop.register_canceller(desktop_controller.emergency_abort)
    vision_service.cleanup_temp_files(max_age_seconds=0)
    timer_scheduler_task = asyncio.create_task(_timer_scheduler_loop())


@app.on_event("shutdown")
def shutdown_event():
    global timer_scheduler_task
    if timer_scheduler_task and not timer_scheduler_task.done():
        timer_scheduler_task.cancel()
    wake_word_service.stop()
    desktop_controller.emergency_abort()
    vision_service.cleanup_temp_files(max_age_seconds=0)
    perception_cache.invalidate_all("Application Shutdown")
    cancel_current_pipeline()


def cancel_current_pipeline() -> None:
    """Cancel any active background recording, inference, TTS synthesis, or audio playback."""
    global current_pipeline_task, current_cancel_event
    if current_cancel_event is not None:
        current_cancel_event.set()
    audio_service.stop()

    if current_pipeline_task and not current_pipeline_task.done():
        current_pipeline_task.cancel()
        current_pipeline_task = None


@app.get("/health")
def health_check():
    return {
        "status": "online",
        "state": CURRENT_STATE,
        "session_id": current_session_id,
        "ollama_connected": ollama_service.check_connection(),
        "ollama_model": ollama_service.model,
        "tts_ready": tts_service.is_ready(),
        "tts_engine": getattr(tts_service, "engine_name", "edge"),
        "tts_voice": getattr(tts_service, "voice_name", "Aria"),
        "available_voices": getattr(tts_service, "get_available_voices", lambda: [])(),
        "tts_sample_rate": getattr(tts_service, "sample_rate", AUDIO_SAMPLE_RATE),
        "stt_loaded": stt_service.is_loaded(),
        "wake_word_active": wake_word_service.is_running,
        "deep_search_active": deep_search_active,
        "vision_ready": True,
        "rag_chunks": rag_service.get_chunk_count(),
        "active_reminders": len(reminder_service.list_active()),
    }


@app.get("/api/wiki-image")
async def proxy_wiki_image(url: str = Query(..., description="HTTPS Wikimedia image URL")):
    """Proxy allowlisted Wikimedia image thumbnails to avoid hotlink/Electron 403 blocks."""
    fetched = await asyncio.to_thread(wiki_service.fetch_image, url)
    if fetched is None:
        raise HTTPException(status_code=404, detail="Image unavailable")
    content, media_type = fetched
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/api/screenshot/latest")
async def get_latest_screenshot():
    """Returns latest desktop screenshot."""
    import os
    latest_path = vision_service.get_latest_screenshot_path()
    if not latest_path or not os.path.exists(latest_path):
        shot = await asyncio.to_thread(vision_service.capture_screen)
        latest_path = shot["image_path"]
    return FileResponse(latest_path, media_type="image/png")


@app.get("/api/documents")
def list_documents():
    """Returns indexed document files and chunk statistics."""
    files = rag_service.list_documents()
    count = rag_service.get_chunk_count()
    return {"documents": files, "chunk_count": count}


@app.post("/api/documents/index")
def reindex_documents():
    """Trigger re-indexing of local documents directory."""
    count = rag_service.index_directory()
    return {"success": True, "indexed_chunks": count}


@app.get("/api/reminders")
def get_active_reminders():
    """Returns active timers and reminders."""
    return {"reminders": reminder_service.list_active()}


@app.get("/api/sandbox/status")
def get_sandbox_status():
    """Returns AURA Security Sandbox configuration and enforcement status."""
    return AuraSandboxProtocol.get_sandbox_status()


@app.delete("/api/reminders/{reminder_id}")
def cancel_reminder(reminder_id: int):
    """Cancel a specific reminder."""
    success = reminder_service.cancel_reminder(reminder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found or already completed")
    return {"success": True, "id": reminder_id}


@app.post("/api/reminders")
def create_scheduled_reminder(payload: dict = Body(...)):
    """Create a new countdown timer or scheduled reminder."""
    title = payload.get("title", "Reminder").strip()
    duration_seconds = float(payload.get("duration_seconds", 60.0))
    is_timer = bool(payload.get("is_timer", True))
    notification_type = str(payload.get("notification_type", "toast"))
    recurrence = payload.get("recurrence")
    email_to = payload.get("email_to")

    res = reminder_service.create_timer(
        duration_seconds=duration_seconds,
        title=title,
        is_timer=is_timer,
        notification_type=notification_type,
        recurrence=recurrence,
        email_to=email_to,
    )
    return {"success": True, "reminder": res}


# --- Email & Reminders Endpoints (Phase V1 Email Integration) ---

@app.get("/api/email/status")
def get_email_status():
    """Returns Gmail connection status, destination email, and toggle states."""
    return email_service.get_status()


@app.post("/api/email/settings")
def update_email_settings(payload: dict = Body(...)):
    """Update destination email and toggle settings."""
    if "destination_email" in payload:
        email_service.set_destination_email(str(payload["destination_email"]))
    if "notifications_enabled" in payload:
        email_service.set_enabled(bool(payload["notifications_enabled"]))
    if "daily_summary_enabled" in payload:
        email_service.set_daily_summary_enabled(bool(payload["daily_summary_enabled"]))
    if "daily_summary_time" in payload:
        email_service.set_daily_summary_time(str(payload["daily_summary_time"]))
    return {"success": True, "status": email_service.get_status()}


@app.post("/api/email/credentials")
def set_email_credentials(payload: dict = Body(...)):
    """Store Google OAuth Client ID and Secret in secure SecretStore."""
    client_id = payload.get("client_id", "").strip()
    client_secret = payload.get("client_secret", "").strip()
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="Client ID and Client Secret are required")
    email_service.set_oauth_client_credentials(client_id, client_secret)
    return {"success": True, "message": "OAuth credentials securely saved."}


@app.get("/api/email/oauth/auth-url")
def get_oauth_auth_url(redirect_uri: Optional[str] = None):
    """Generate Google OAuth consent URL for minimal gmail.send scope."""
    uri = redirect_uri or "http://127.0.0.1:8000/api/email/oauth/callback"
    res = email_service.generate_auth_url(redirect_uri=uri)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@app.get("/api/email/oauth/callback")
def oauth_callback(code: Optional[str] = None, error: Optional[str] = None):
    """Handles Google OAuth redirect, exchanges code for tokens, and returns clean HTML redirect."""
    if error:
        return Response(
            content=f"<html><body><h3>Google OAuth Error</h3><p>{error}</p><script>window.close();</script></body></html>",
            media_type="text/html",
        )
    if not code:
        return Response(content="<html><body><h3>No authorization code provided.</h3></body></html>", media_type="text/html")

    res = email_service.exchange_code_for_tokens(code)
    if res.get("success"):
        return Response(
            content="""
            <html>
            <head><title>Gmail Connected</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 40px; background: #f8fafc;">
                <h2 style="color: #4f46e5;">✨ Gmail Successfully Connected to AURA!</h2>
                <p style="color: #475569;">You can now close this tab and return to the AURA desktop application.</p>
                <script>
                    if (window.opener) {
                        window.opener.postMessage({ type: 'GMAIL_OAUTH_SUCCESS' }, '*');
                    }
                    setTimeout(() => window.close(), 2500);
                </script>
            </body>
            </html>
            """,
            media_type="text/html",
        )
    else:
        return Response(
            content=f"<html><body><h3>Connection Failed</h3><p>{res.get('error')}</p></body></html>",
            media_type="text/html",
        )


@app.post("/api/email/disconnect")
def disconnect_email():
    """Disconnect connected Gmail account and wipe OAuth tokens."""
    return email_service.disconnect()


@app.post("/api/email/send-test")
def send_test_email(payload: dict = Body(default={})):
    """Send test email notification."""
    target = payload.get("to_email")
    res = email_service.send_test_email(to_email=target)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to send test email"))
    return res


@app.post("/api/email/send-summary-now")
def send_summary_now(payload: dict = Body(default={})):
    """Trigger daily summary digest email on demand."""
    target = payload.get("to_email")
    res = daily_summary_service.send_summary_now(to_email=target)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to send daily summary"))
    return res


@app.get("/api/email/history")
def get_email_history(limit: int = 20):
    """Retrieve recent email delivery audit log."""
    return {"logs": email_service.get_delivery_history(limit=limit)}


@app.get("/api/email/notes")
def get_important_notes(unemailed: bool = False):
    """List saved important notes."""
    return {"notes": important_notes_service.list_notes(only_unemailed=unemailed)}


@app.post("/api/email/notes")
def create_important_note(payload: dict = Body(...)):
    """Create a new important note with optional immediate email dispatch."""
    content = payload.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")
    category = payload.get("category", "general")
    email_now = bool(payload.get("email_now", False))

    note = important_notes_service.add_note(content, category=category, emailed=email_now)
    email_res = None
    if email_now:
        email_res = email_service.send_email(
            subject="📌 Important Note from AURA",
            body_text=f"Important Information:\n\n{content}",
        )
    return {"success": True, "note": note, "email": email_res}


@app.delete("/api/email/notes/{note_id}")
def delete_important_note(note_id: int):
    """Delete an important note."""
    ok = important_notes_service.delete_note(note_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"success": True, "id": note_id}


# --- Windows Cursor Management Endpoints ---

@app.get("/api/cursor/status")
def get_cursor_status():
    """Returns Windows system-wide cursor status, asset readiness, and backup state."""
    return windows_cursor_service.get_status()


@app.post("/api/cursor/system/apply")
def apply_system_cursor():
    """Applies Kawaii Pixel Cat Paw animated theme to Windows system-wide."""
    return windows_cursor_service.apply_cat_paw_system_wide()


@app.post("/api/cursor/system/restore")
def restore_system_cursor():
    """Restores previous Windows cursor theme from backup."""
    return windows_cursor_service.restore_previous_system_theme()


# --- AURA Independent Virtual Assistant Hand & Skin Library Endpoints ---

@app.get("/api/virtual-hand/themes")
def get_virtual_hand_themes():
    """Lists all available cursor skins and active theme configuration."""
    themes = virtual_hand_theme_service.list_themes()
    active_id = virtual_hand_theme_service.get_active_theme_id()
    return {"themes": themes, "active_theme_id": active_id}


@app.get("/api/virtual-hand/themes/active")
def get_active_virtual_hand_theme():
    """Returns the resolved active theme manifest and image assets."""
    return virtual_hand_theme_service.get_active_theme()


@app.post("/api/virtual-hand/themes/active")
def set_active_virtual_hand_theme(payload: dict = Body(...)):
    """Switches the active virtual hand theme."""
    theme_id = payload.get("theme_id", "")
    ok = virtual_hand_theme_service.set_active_theme(theme_id)
    if ok:
        virtual_hand_controller.broadcast({"type": "theme_changed", "theme_id": theme_id})
        return {"success": True, "active_theme_id": theme_id}
    return {"success": False, "error": f"Failed to activate theme '{theme_id}'"}


@app.post("/api/virtual-hand/themes/upload")
def upload_virtual_hand_theme(payload: dict = Body(...)):
    """Safely inspects and imports a cursor skin (.zip, .ani, .cur, .gif, .png, .webp) via base64."""
    filename = payload.get("filename", "theme.zip")
    custom_name = payload.get("custom_name")
    raw_b64 = payload.get("content_base64", "")
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]
    try:
        content = base64.b64decode(raw_b64)
    except Exception as e:
        return {"success": False, "error": f"Invalid base64 payload: {e}"}

    res = virtual_hand_theme_service.import_theme(filename, content, custom_name=custom_name)
    if res.get("success"):
        virtual_hand_controller.broadcast({"type": "theme_changed", "theme_id": res["theme"]["id"]})
    return res


@app.post("/api/virtual-hand/themes/settings")
def update_virtual_hand_settings(payload: dict = Body(...)):
    """Updates size, speed, hotspot, and animation settings for a theme."""
    theme_id = payload.get("theme_id", "")
    settings = payload.get("settings", {})
    res = virtual_hand_theme_service.update_theme_settings(theme_id, settings)
    if res.get("success"):
        virtual_hand_controller.broadcast({"type": "theme_changed", "theme_id": theme_id})
    return res


@app.delete("/api/virtual-hand/themes/{theme_id}")
def delete_virtual_hand_theme(theme_id: str):
    """Deletes a custom user theme (built-in themes protected)."""
    res = virtual_hand_theme_service.delete_theme(theme_id)
    if res.get("success"):
        virtual_hand_controller.broadcast({"type": "theme_changed"})
    return res


@app.post("/api/virtual-hand/themes/reset-default")
def reset_virtual_hand_theme():
    """Restores the default Kawaii Pixel Cat Paw assistant claw."""
    virtual_hand_theme_service.set_active_theme("kawaii_cat_paw")
    virtual_hand_controller.broadcast({"type": "theme_changed", "theme_id": "kawaii_cat_paw"})
    return {"success": True, "active_theme_id": "kawaii_cat_paw"}


@app.post("/api/virtual-hand/test-glide")
def test_virtual_hand_glide():
    """Triggers a graceful arc test movement and click across screen for visual verification."""
    screen_w, screen_h = desktop_controller.mouse.get_screen_resolution()
    start_x = int(screen_w * 0.25)
    start_y = int(screen_h * 0.35)
    target_x = int(screen_w * 0.65)
    target_y = int(screen_h * 0.45)

    virtual_hand_controller.show(start_x, start_y, state="normal")
    time.sleep(0.1)
    virtual_hand_controller.move_to(target_x, target_y, duration=0.6, state="pointer", sync_system_mouse=False)
    time.sleep(0.65)
    virtual_hand_controller.click(target_x, target_y, button="left")
    time.sleep(0.3)
    virtual_hand_controller.hide()
    return {"success": True, "message": "Virtual hand test glide completed."}


# -------------------------------------------------------------
# AURA Dynamic Personality & Social Behaviour REST Endpoints
# -------------------------------------------------------------
@app.get("/api/personality")
def get_personality_status():
    """Returns AURA Dynamic Personality settings, active profile, and voice/expression mappings."""
    return {
        "settings": personality_service.get_settings().to_dict(),
        "profiles": [p.value for p in PersonalityProfile],
        "mood": personality_service.get_companion_mood(),
        "voice": personality_service.get_voice_parameters(),
    }


@app.post("/api/personality")
async def update_personality_settings(payload: dict = Body(...)):
    """Updates personality sliders, explanation depth, and auto-switching."""
    updated = personality_service.update_settings(payload)
    await broadcast({
        "type": "personality_update",
        "settings": updated.to_dict(),
        "mood": personality_service.get_companion_mood(),
        "voice": personality_service.get_voice_parameters(),
    })
    return {"success": True, "settings": updated.to_dict()}


@app.post("/api/personality/profile")
async def set_personality_profile(payload: dict = Body(...)):
    """Switches active personality profile."""
    profile = payload.get("profile", PersonalityProfile.NORMAL.value)
    temporary = bool(payload.get("temporary", False))
    updated = personality_service.set_active_profile(profile, temporary=temporary)
    await broadcast({
        "type": "personality_update",
        "settings": updated.to_dict(),
        "mood": personality_service.get_companion_mood(),
        "voice": personality_service.get_voice_parameters(),
    })
    return {"success": True, "settings": updated.to_dict()}


@app.post("/api/personality/reset")
async def reset_personality_profile():
    """Resets active personality profile to the saved default."""
    updated = personality_service.reset_to_default()
    await broadcast({
        "type": "personality_update",
        "settings": updated.to_dict(),
        "mood": personality_service.get_companion_mood(),
        "voice": personality_service.get_voice_parameters(),
    })
    return {"success": True, "settings": updated.to_dict()}


@app.websocket("/api/desktop/virtual-hand-stream")
async def virtual_hand_stream_endpoint(websocket: WebSocket):
    """Real-time event stream for the transparent desktop virtual hand overlay."""
    await websocket.accept()
    virtual_hand_controller.register_subscriber(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"VirtualHand stream disconnect: {e}")
    finally:
        virtual_hand_controller.unregister_subscriber(websocket)


# --- Desktop Interaction & Hardware Automation Endpoints ---

@app.get("/api/desktop/status")
def get_desktop_status():
    """Returns desktop display resolution, virtual coordinates, monitors, and active window."""
    monitors = desktop_controller.mouse.get_monitors()
    pos = desktop_controller.mouse.get_position()
    active_win = desktop_controller.windows.get_foreground_window()
    return {
        "status": "active",
        "emergency_stop": emergency_stop.is_stopped(),
        "mouse_position": {"x": pos[0], "y": pos[1]},
        "monitors": monitors,
        "foreground_window": active_win,
    }


@app.get("/api/desktop/windows")
def list_desktop_windows():
    """Lists open top-level application windows on user desktop."""
    return {"windows": desktop_controller.windows.list_windows()}


@app.post("/api/desktop/mouse/move")
def desktop_mouse_move(payload: dict = Body(...)):
    """Smoothly moves mouse pointer to (x, y) coordinates."""
    x = int(payload.get("x", 0))
    y = int(payload.get("y", 0))
    smooth = bool(payload.get("smooth", True))
    duration = float(payload.get("duration", 0.3))
    ok = desktop_controller.mouse.move_to(x, y, smooth=smooth, duration=duration)
    return {"success": ok, "x": x, "y": y}


@app.post("/api/desktop/mouse/click")
def desktop_mouse_click(payload: dict = Body(default={})):
    """Performs single, double, or right mouse click."""
    x = payload.get("x")
    y = payload.get("y")
    button = payload.get("button", "left")
    clicks = int(payload.get("clicks", 1))
    ok = desktop_controller.mouse.click(x=x, y=y, button=button, clicks=clicks)
    return {"success": ok, "button": button, "clicks": clicks}


@app.post("/api/desktop/mouse/scroll")
def desktop_mouse_scroll(payload: dict = Body(default={})):
    """Scrolls mouse wheel vertically or horizontally."""
    clicks = int(payload.get("clicks", 3))
    horizontal = bool(payload.get("horizontal", False))
    ok = desktop_controller.mouse.scroll(clicks=clicks, horizontal=horizontal)
    return {"success": ok, "clicks": clicks, "horizontal": horizontal}


@app.post("/api/desktop/keyboard/type")
def desktop_keyboard_type(payload: dict = Body(...)):
    """Types Unicode text into focused window using hardware SendInput."""
    text = payload.get("text", "")
    ok = desktop_controller.keyboard.type_text(text)
    return {"success": ok, "length": len(text)}


@app.post("/api/desktop/keyboard/hotkey")
def desktop_keyboard_hotkey(payload: dict = Body(...)):
    """Executes keyboard shortcut combination."""
    keys = payload.get("keys", [])
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split("+")]
    ok = desktop_controller.keyboard.hotkey(*keys)
    return {"success": ok, "keys": keys}


@app.post("/api/desktop/window/focus")
def desktop_window_focus(payload: dict = Body(...)):
    """Brings target window to foreground."""
    target = payload.get("target")
    ok = desktop_controller.windows.focus_window(target)
    return {"success": ok, "target": target}


@app.post("/api/desktop/open-app")
def desktop_open_app(payload: dict = Body(...)):
    """Launches or focuses application."""
    app_name = payload.get("app_name", "")
    res = desktop_controller.open_app(app_name)
    return res


@app.post("/api/desktop/emergency-abort")
def desktop_emergency_abort():
    """Failsafe: releases all held mouse buttons and keys, resets automation."""
    res = desktop_controller.emergency_abort()
    return res


# --- Resource Efficiency, Perception Cache & Telemetry Endpoints ---

@app.get("/api/system/resource-metrics")
def get_resource_metrics():
    """Returns real-time RAM, GPU VRAM, CPU, latencies, cache metrics, and model resident states."""
    return resource_monitor.get_metrics()


@app.get("/api/perception/cache-status")
def get_perception_cache_status():
    """Returns perception and OCR cache telemetry and memory utilization."""
    return perception_cache.get_stats()


@app.post("/api/perception/cache-clear")
def clear_perception_cache():
    """Clears all cached screen perception & OCR entries, and runs garbage collection."""
    cleared = perception_cache.invalidate_all("Manual Clear via API")
    return {"success": True, "cleared_entries": cleared}


@app.post("/api/perception/cleanup-temp")
def cleanup_temp_screenshots():
    """Safely removes lingering temporary screenshot files from disk."""
    deleted = vision_service.cleanup_temp_files(max_age_seconds=0)
    return {"success": True, "deleted_files": deleted}


@app.post("/api/system/models/unload")
def unload_gpu_models():
    """Unloads vision and LLM models from GPU VRAM and clears CUDA cache."""
    return vision_service.unload_vision_models()


# --- Zero-Trust Security Endpoints ---

@app.get("/api/security/status")
def get_security_status():
    """Returns comprehensive zero-trust security configuration, active protections, and audit stats."""
    return {
        "policy": "AURA-ZERO-TRUST-v1.0",
        "emergency_stop": {
            "active": emergency_stop.is_stopped(),
            "status": "STOPPED" if emergency_stop.is_stopped() else "OPERATIONAL",
        },
        "process_isolation": {
            "active": process_sandbox.is_supported,
            "mechanism": "Windows Job Object (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | 2GB Virtual Memory Cap)",
            "active_processes": process_sandbox.get_active_process_count(),
        },
        "filesystem_guard": {
            "enforced": True,
            "allowed_roots": [str(r) for r in filesystem_guard.allowed_roots],
            "backup_directory": str(filesystem_guard.backup_dir),
            "traversal_protection": True,
        },
        "network_guard": {
            "ssrf_defense_active": True,
            "blocked_ip_ranges": [
                "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
                "127.0.0.0/8", "169.254.0.0/16", "::1", "fc00::/7"
            ],
            "max_download_mb": 100,
            "blocked_extensions": list(network_guard.BLOCKED_EXTENSIONS),
        },
        "prompt_guard": {
            "dual_zone_cognitive_provenance": True,
            "injection_patterns_loaded": len(prompt_guard.INJECTION_PATTERNS),
        },
        "secret_store": {
            "isolated_credentials_path": str(secret_store.credentials_file),
            "log_redaction_active": True,
        },
        "pending_approvals_count": len(permission_gateway.list_pending_approvals()),
        "audit_statistics": audit_logger.get_statistics(),
    }


@app.get("/api/security/audit-events")
def get_audit_events(limit: int = 100):
    """Returns recent structured audit events."""
    return {"events": audit_logger.get_recent_events(limit=limit)}


@app.get("/api/security/pending-approvals")
def get_pending_approvals():
    """Returns currently pending Level 2/Level 3 approval requests."""
    return {"pending_approvals": permission_gateway.list_pending_approvals()}


@app.post("/api/security/approve/{approval_id}")
async def approve_security_request(approval_id: str):
    """User approves a pending Level 2 or Level 3 operation."""
    success, result_or_err = await asyncio.to_thread(permission_gateway.approve, approval_id)
    if not success:
        raise HTTPException(status_code=400, detail=result_or_err)
    await broadcast({
        "type": "approval_resolved",
        "approval_id": approval_id,
        "status": "APPROVED",
        "result": result_or_err,
    })
    return {"success": True, "result": result_or_err}


@app.post("/api/security/reject/{approval_id}")
def reject_security_request(approval_id: str, reason: str = "User rejected via Security Dashboard"):
    """User rejects a pending operation."""
    success, err = permission_gateway.reject(approval_id, reason=reason)
    if not success:
        raise HTTPException(status_code=400, detail=err)
    return {"success": True, "approval_id": approval_id}


@app.post("/api/security/emergency-stop")
async def trigger_emergency_stop():
    """Global Emergency Stop: terminates sandboxed processes, cancels pipelines, revokes approvals."""
    cancel_current_pipeline()
    emergency_stop.trigger(reason="Manual Emergency Stop invoked via Security Dashboard")
    await set_state("IDLE")
    await broadcast({
        "type": "emergency_stop",
        "status": "STOPPED",
        "message": "EMERGENCY STOP TRIGGERED: All child processes killed and operations halted.",
    })
    return {"success": True, "status": "EMERGENCY_STOPPED"}


@app.post("/api/security/emergency-reset")
async def reset_emergency_stop():
    """Resets the Emergency Stop state back to normal operational status."""
    emergency_stop.reset()
    await broadcast({
        "type": "emergency_reset",
        "status": "OPERATIONAL",
        "message": "Emergency Stop reset. Normal operations resumed.",
    })
    return {"success": True, "status": "OPERATIONAL"}


def _sanitize_llm_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    """
    Ensure conversation history strictly alternates user -> assistant before the final user message.
    Prevents orphaned/aborted user turns from causing the LLM to re-answer prior prompts.
    """
    if not history:
        return []

    prior = history[:-1]
    latest = history[-1]

    clean_pairs: list[dict[str, str]] = []
    idx = 0
    while idx + 1 < len(prior):
        if prior[idx].get("role") == "user" and prior[idx + 1].get("role") == "assistant":
            clean_pairs.append(prior[idx])
            clean_pairs.append(prior[idx + 1])
            idx += 2
        else:
            idx += 1

    clean_pairs.append(latest)
    return clean_pairs


async def _stream_llm_and_speak(
    history: list[dict[str, str]],
    this_task: Optional[asyncio.Task],
    session_id_for_turn: int,
    system_prompt: Optional[str] = None,
) -> str:
    """
    Stream Ollama tokens -> split natural sentences -> stream Piper PCM chunks -> play continuously.
    Persists generated assistant text even if audio playback is cancelled mid-speech.
    """
    global current_cancel_event
    cancel_event = threading.Event()
    current_cancel_event = cancel_event
    loop = asyncio.get_running_loop()

    sentence_queue: queue.Queue[Optional[str]] = queue.Queue()
    pcm_queue: queue.Queue[Optional[object]] = queue.Queue(maxsize=32)
    full_reply_parts: list[str] = []
    saved_to_db = False

    def _emit_ws(payload: dict) -> None:
        if not cancel_event.is_set():
            asyncio.run_coroutine_threadsafe(broadcast(payload), loop)

    def _persist_reply_if_needed() -> str:
        nonlocal saved_to_db
        reply_text = "".join(full_reply_parts).strip()
        if reply_text and not saved_to_db:
            storage.add_message(session_id_for_turn, "assistant", reply_text)
            saved_to_db = True
        return reply_text

    def _llm_producer() -> None:
        buf = ""
        is_first_chunk = True
        active_prompt = system_prompt or SYSTEM_PROMPT
        try:
            for token in ollama_service.chat_stream(history, system_prompt=active_prompt, cancel_event=cancel_event):
                if cancel_event.is_set():
                    break
                full_reply_parts.append(token)
                buf += token
                _emit_ws({"type": "response_chunk", "text": "".join(full_reply_parts)})

                if is_first_chunk:
                    # Early phrasal splitting for chunk #1 to achieve sub-second Time-To-First-Audio (TTFA)
                    # Splits on commas, semicolons, dashes, exclamations, or question marks early
                    m = _FIRST_CLAUSE_SPLIT_RE.search(buf)
                    matched_end = m.end() if m else 0
                    if m and (
                        (matched_end >= 4 and m.group().strip() in (".", "!", "?", "\n"))
                        or (matched_end >= 8)
                    ):
                        first_clause = buf[:matched_end].strip()
                        buf = buf[matched_end:].lstrip()
                        if first_clause:
                            sentence_queue.put(first_clause)
                            is_first_chunk = False
                    elif len(buf) >= 32:
                        # Fallback if first sentence is long without early punctuation
                        space_idx = buf.rfind(" ", 12, 32)
                        if space_idx > 0:
                            first_clause = buf[:space_idx].strip()
                            buf = buf[space_idx:].lstrip()
                            if first_clause:
                                sentence_queue.put(first_clause)
                                is_first_chunk = False
                else:
                    # Normal sentence splitting for subsequent chunks
                    match = _SENTENCE_SPLIT_RE.search(buf)
                    if match and match.end() >= 16:
                        sentence = buf[: match.end()].strip()
                        buf = buf[match.end() :].lstrip()
                        if sentence:
                            sentence_queue.put(sentence)
                    elif len(buf) >= 75:
                        # Prevent exceptionally long sentences from stalling the playback buffer
                        clause_match = _LONG_CLAUSE_SPLIT_RE.search(buf)
                        if clause_match and clause_match.end() >= 35:
                            sub_clause = buf[: clause_match.end()].strip()
                            buf = buf[clause_match.end() :].lstrip()
                            if sub_clause:
                                sentence_queue.put(sub_clause)

            if not cancel_event.is_set() and buf.strip():
                sentence_queue.put(buf.strip())

            # Persist full assistant reply as soon as LLM generation finishes (before playback ends)
            final_text = _persist_reply_if_needed()
            if final_text and not cancel_event.is_set():
                _emit_ws({"type": "response", "text": final_text})
        except Exception as exc:
            logger.error(f"LLM stream producer error: {exc}", exc_info=True)
        finally:
            sentence_queue.put(None)

    def _tts_worker() -> None:
        try:
            while not cancel_event.is_set():
                sentence = sentence_queue.get()
                if sentence is None:
                    break
                for pcm_chunk in tts_service.synthesize_pcm_stream(sentence, cancel_event=cancel_event):
                    if cancel_event.is_set():
                        break
                    pcm_queue.put(pcm_chunk)
        except Exception as exc:
            logger.error(f"TTS worker error: {exc}", exc_info=True)
        finally:
            pcm_queue.put(None)

    def _pcm_chunk_iterator():
        while not cancel_event.is_set():
            chunk = pcm_queue.get()
            if chunk is None:
                break
            yield chunk

    def _run_pipeline_threads() -> None:
        v_params = personality_service.get_voice_parameters()
        tts_service.set_delivery_tuning(
            rate=v_params.get("rate_str", "+0%"),
            pitch=v_params.get("pitch", "+0Hz"),
            length_scale=1.0 / v_params.get("rate", 1.0),
        )
        llm_t = threading.Thread(target=_llm_producer, daemon=True)
        tts_t = threading.Thread(target=_tts_worker, daemon=True)
        llm_t.start()
        tts_t.start()

        try:
            def _on_chunk_level(lvl: float) -> None:
                if not cancel_event.is_set():
                    asyncio.run_coroutine_threadsafe(
                        broadcast({"type": "level", "value": round(lvl, 3)}), loop
                    )

            active_sr = getattr(tts_service, "sample_rate", AUDIO_SAMPLE_RATE)
            audio_service.play_pcm_stream(
                _pcm_chunk_iterator(),
                sample_rate=active_sr,
                on_playback_start=lambda: (
                    asyncio.run_coroutine_threadsafe(set_state("SPEAKING"), loop)
                    if not cancel_event.is_set()
                    else None
                ),
                on_chunk_played=_on_chunk_level,
            )
        finally:
            llm_t.join(timeout=2.0)
            tts_t.join(timeout=2.0)

    try:
        t0 = time.perf_counter()
        await asyncio.to_thread(_run_pipeline_threads)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        reply = _persist_reply_if_needed()
        if reply and not cancel_event.is_set():
            logger.info(f"Streaming response completed in {elapsed_ms:.0f} ms.")
        return reply
    except asyncio.CancelledError:
        cancel_event.set()
        audio_service.stop()
        _persist_reply_if_needed()
        # Drain sentinels if threads are waiting
        try:
            sentence_queue.put_nowait(None)
        except Exception:
            pass
        try:
            pcm_queue.put_nowait(None)
        except Exception:
            pass
        raise
    finally:
        if current_cancel_event is cancel_event:
            current_cancel_event = None


async def _speak_tool_response(spoken_text: str, this_task: Optional[asyncio.Task]) -> None:
    """Synthesize and stream audio response for a system tool action."""
    if not spoken_text.strip():
        await set_state("IDLE")
        return

    global current_cancel_event
    cancel_event = threading.Event()
    current_cancel_event = cancel_event
    loop = asyncio.get_running_loop()

    def _play_speech():
        try:
            v_params = personality_service.get_voice_parameters()
            tts_service.set_delivery_tuning(
                rate=v_params.get("rate_str", "+0%"),
                pitch=v_params.get("pitch", "+0Hz"),
                length_scale=1.0 / v_params.get("rate", 1.0),
            )

            def _on_chunk_level(lvl: float) -> None:
                if not cancel_event.is_set():
                    asyncio.run_coroutine_threadsafe(
                        broadcast({"type": "level", "value": round(lvl, 3)}), loop
                    )

            chunks = tts_service.synthesize_pcm_stream(spoken_text, cancel_event=cancel_event)
            active_sr = getattr(tts_service, "sample_rate", AUDIO_SAMPLE_RATE)
            audio_service.play_pcm_stream(
                chunks,
                sample_rate=active_sr,
                on_playback_start=lambda: (
                    asyncio.run_coroutine_threadsafe(set_state("SPEAKING"), loop)
                    if not cancel_event.is_set()
                    else None
                ),
                on_chunk_played=_on_chunk_level,
            )
        except Exception as e:
            logger.error(f"Error speaking tool response: {e}")
        finally:
            if not cancel_event.is_set():
                asyncio.run_coroutine_threadsafe(set_state("IDLE"), loop)

    try:
        await asyncio.to_thread(_play_speech)
    finally:
        if current_cancel_event is cancel_event:
            current_cancel_event = None
        if not cancel_event.is_set():
            await set_state("IDLE")


async def _run_query_and_respond(user_text: str, this_task: Optional[asyncio.Task]) -> None:
    """
    Shared handler for both voice and text inputs:
    Saves prompt -> checks Phase 7 system tools -> optional Wikipedia deep search -> streams Ollama & Piper PCM.
    """
    session_id = current_session_id
    storage.add_message(session_id, "user", user_text)

    # Dynamic Personality Natural-Language Manual Command Interceptor
    pers_cmd = personality_service.check_manual_command(user_text)
    if pers_cmd:
        new_prof, is_temp, spoken = pers_cmd
        storage.add_message(session_id, "assistant", spoken)
        await broadcast({
            "type": "personality_update",
            "settings": personality_service.get_settings().to_dict(),
            "profile": new_prof,
            "mood": personality_service.get_companion_mood(new_prof),
            "voice": personality_service.get_voice_parameters(new_prof),
        })
        await broadcast({"type": "response", "text": spoken})
        await _speak_tool_response(spoken, this_task)
        return

    # AURA Universal Action Planner: Orchestrates multi-step workflows, window management, files, dev tools, and apps
    tool_action = await asyncio.to_thread(ActionPlanner.plan_and_execute, user_text)
    if tool_action and tool_action.get("handled"):
        spoken = tool_action.get("spoken_response") or tool_action.get("message", "")
        action_payload = {
            "type": "system_action",
            "action": tool_action.get("action"),
            "tool_type": tool_action.get("type"),
            "title": tool_action.get("title"),
            "message": tool_action.get("message"),
            "spoken_response": spoken,
            "data": tool_action.get("data", {}),
        }
        await broadcast(action_payload)
        storage.add_message(session_id, "assistant", spoken)
        await broadcast({"type": "response", "text": spoken})
        await _speak_tool_response(spoken, this_task)
        return

    history = storage.get_recent_messages(session_id, limit=6)

    # Automatic Context-Aware Personality Inference (when enabled and no temporary lock)
    inferred_profile = personality_service.infer_context_profile(user_text, list(history))
    if inferred_profile:
        personality_service.set_active_profile(inferred_profile, temporary=True)
        await broadcast({
            "type": "personality_update",
            "settings": personality_service.get_settings().to_dict(),
            "profile": inferred_profile,
            "mood": personality_service.get_companion_mood(inferred_profile),
            "voice": personality_service.get_voice_parameters(inferred_profile),
        })

    # Phase 9: Ground with local personal knowledge (RAG)
    rag_context = ""
    try:
        rag_matches = await asyncio.to_thread(rag_service.search, user_text, 2)
        if rag_matches and rag_matches[0].get("score", 0) >= 1.5:
            rag_context = rag_service.format_context_for_prompt(rag_matches)
    except Exception as e:
        logger.debug(f"RAG search error: {e}")

    should_wiki, wiki_query = wiki_service.should_search(
        user_text, deep_search_enabled=deep_search_active, history=list(history)
    )
    llm_history = _sanitize_llm_history(list(history))

    if rag_context and llm_history:
        llm_history[-1]["content"] = f"{llm_history[-1]['content']}\n\n{rag_context}"

    if should_wiki:
        await broadcast({"type": "info", "message": f"Deep searching Wikipedia: '{wiki_query}'..."})
        wiki_result = await asyncio.to_thread(wiki_service.deep_search, wiki_query)
        if wiki_result:
            await broadcast({
                "type": "wiki_results",
                "query": wiki_result["query"],
                "articles": wiki_result["articles"],
                "images": wiki_result["images"],
            })
            wiki_context = wiki_service.format_context_for_llm(wiki_result)
            has_images = bool(wiki_result.get("images"))
            visual_note = (
                "Visual Note: Wikipedia article and high-resolution gallery images for this topic ARE actively displayed on the user's screen right now. "
                "Directly acknowledge and introduce the displayed images. NEVER say you cannot display images or access Wikipedia. "
                if has_images
                else ""
            )
            if wiki_context:
                # Isolate fresh encyclopedic search from unrelated prior coding/chat context
                llm_history = [
                    {
                        "role": "user",
                        "content": (
                            f"{user_text}\n\n{wiki_context}\n\n{visual_note}"
                            "Answer ONLY this current request in 1 to 3 concise spoken sentences."
                        ),
                    }
                ]

    # Compose dynamic personality-enhanced system prompt
    active_sys_prompt = SYSTEM_PROMPT + personality_service.generate_system_prompt_instructions()
    companion_mood = personality_service.get_companion_mood()
    await broadcast({"type": "companion_mood", "mood": companion_mood})

    await _stream_llm_and_speak(llm_history, this_task, session_id, system_prompt=active_sys_prompt)


async def run_voice_pipeline() -> None:
    """Voice pipeline with pre-roll recording, CPU INT8 STT, Wikipedia deep search, and streaming TTS."""
    if emergency_stop.is_stopped():
        await broadcast({"type": "error", "message": "EMERGENCY STOP ACTIVE: Voice pipeline execution halted by safety protocol."})
        return
    this_task = asyncio.current_task()
    try:
        await asyncio.to_thread(stt_service.load_model)
        await set_state("LISTENING")
        await broadcast({"type": "info", "message": "Listening for speech..."})

        # Play brief ascending chime before microphone opens to prevent acoustic self-recording
        await asyncio.to_thread(audio_service.play_listening_chime, True)

        # Step 1: Record Speech
        audio_data = await asyncio.to_thread(
            audio_service.record_speech,
            INPUT_SAMPLE_RATE,
            SILENCE_ENERGY_THRESHOLD,
            SILENCE_DURATION_SECONDS,
            MAX_RECORDING_DURATION,
        )

        if len(audio_data) == 0:
            if current_pipeline_task in (None, this_task):
                await broadcast({"type": "info", "message": "No speech detected."})
                await set_state("IDLE")
            return

        # Step 2: Transcribe Speech
        await set_state("THINKING")
        t_stt = time.perf_counter()
        transcription = await asyncio.to_thread(stt_service.transcribe, audio_data)
        logger.info(f"STT transcribed in {(time.perf_counter() - t_stt) * 1000:.0f} ms.")

        if not transcription.strip():
            if current_pipeline_task in (None, this_task):
                await broadcast({"type": "info", "message": "Speech unintelligible."})
                await set_state("IDLE")
            return

        await broadcast({"type": "transcription", "text": transcription})
        await _run_query_and_respond(transcription, this_task)

        if current_pipeline_task in (None, this_task):
            await set_state("IDLE")

    except asyncio.CancelledError:
        logger.info("Voice pipeline was cancelled by user.")
        audio_service.stop()
        if current_pipeline_task in (None, this_task):
            await broadcast({"type": "info", "message": "Cancelled."})
            await set_state("IDLE")
    except Exception as e:
        logger.error(f"Voice pipeline error: {e}", exc_info=True)
        await broadcast({"type": "error", "message": str(e)})
        await set_state("ERROR")
        await asyncio.sleep(2.0)
        if current_pipeline_task in (None, this_task):
            await set_state("IDLE")


async def run_text_pipeline(prompt: str) -> None:
    """Manual text pipeline with Wikipedia deep search, streaming LLM -> TTS, and cancellation."""
    if emergency_stop.is_stopped():
        await broadcast({"type": "error", "message": "EMERGENCY STOP ACTIVE: Text pipeline execution halted by safety protocol."})
        return
    this_task = asyncio.current_task()
    try:
        await set_state("THINKING")
        await broadcast({"type": "transcription", "text": prompt})
        await _run_query_and_respond(prompt, this_task)

        if current_pipeline_task in (None, this_task):
            await set_state("IDLE")

    except asyncio.CancelledError:
        logger.info("Text pipeline was cancelled by user.")
        audio_service.stop()
        if current_pipeline_task in (None, this_task):
            await broadcast({"type": "info", "message": "Cancelled."})
            await set_state("IDLE")
    except Exception as e:
        logger.error(f"Text pipeline error: {e}", exc_info=True)
        await broadcast({"type": "error", "message": str(e)})
        await set_state("ERROR")
        await asyncio.sleep(2.0)
        if current_pipeline_task in (None, this_task):
            await set_state("IDLE")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global current_session_id, current_pipeline_task, deep_search_active
    await websocket.accept()
    active_connections.add(websocket)

    # Initial state payload
    history = storage.get_recent_messages(current_session_id, limit=10)
    await websocket.send_text(
        json.dumps({
            "type": "state_change",
            "state": CURRENT_STATE,
            "model": ollama_service.model,
            "voice": tts_service.voice_name,
            "available_voices": tts_service.get_available_voices(),
            "tts_engine": tts_service.engine_name,
            "wake_word_active": wake_word_service.is_running,
            "deep_search_active": deep_search_active,
            "session_id": current_session_id,
            "history": history,
            "vram_used": 2.5,
            "vram_total": 4.0,
            "personality": personality_service.get_settings().to_dict(),
            "companion_mood": personality_service.get_companion_mood(),
        })
    )

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            msg_type = data.get("type")

            if msg_type == "get_state":
                await websocket.send_text(
                    json.dumps({
                        "type": "state_change",
                        "state": CURRENT_STATE,
                        "model": ollama_service.model,
                        "voice": tts_service.voice_name,
                        "available_voices": tts_service.get_available_voices(),
                        "tts_engine": tts_service.engine_name,
                        "wake_word_active": wake_word_service.is_running,
                        "deep_search_active": deep_search_active,
                        "session_id": current_session_id,
                        "personality": personality_service.get_settings().to_dict(),
                        "companion_mood": personality_service.get_companion_mood(),
                    })
                )

            elif msg_type == "get_personality":
                await websocket.send_text(
                    json.dumps({
                        "type": "personality_update",
                        "settings": personality_service.get_settings().to_dict(),
                        "mood": personality_service.get_companion_mood(),
                        "voice": personality_service.get_voice_parameters(),
                    })
                )

            elif msg_type == "set_personality":
                new_settings = personality_service.update_settings(data.get("settings", {}))
                await broadcast({
                    "type": "personality_update",
                    "settings": new_settings.to_dict(),
                    "mood": personality_service.get_companion_mood(),
                    "voice": personality_service.get_voice_parameters(),
                })

            elif msg_type == "set_personality_profile":
                prof = data.get("profile", "normal")
                temp = bool(data.get("temporary", False))
                new_settings = personality_service.set_active_profile(prof, temporary=temp)
                await broadcast({
                    "type": "personality_update",
                    "settings": new_settings.to_dict(),
                    "mood": personality_service.get_companion_mood(),
                    "voice": personality_service.get_voice_parameters(),
                })

            elif msg_type == "reset_personality":
                new_settings = personality_service.reset_to_default()
                await broadcast({
                    "type": "personality_update",
                    "settings": new_settings.to_dict(),
                    "mood": personality_service.get_companion_mood(),
                    "voice": personality_service.get_voice_parameters(),
                })

            elif msg_type == "start_listening":
                # Interruption handling: Cancel any prior active pipeline and transition to listening
                if CURRENT_STATE != "IDLE" or (current_pipeline_task and not current_pipeline_task.done()):
                    cancel_current_pipeline()
                current_pipeline_task = asyncio.create_task(run_voice_pipeline())

            elif msg_type in ("stop_audio", "cancel", "stop_listening"):
                # Complete cancellation: halts playback and background task
                cancel_current_pipeline()
                audio_service.play_cancel_chime()
                await set_state("IDLE")

            elif msg_type in ("set_voice", "voice"):
                voice_id = data.get("voice") or data.get("name")
                if voice_id:
                    updated_profile = tts_service.set_voice(voice_id)
                    await broadcast({
                        "type": "voice_updated",
                        "voice": tts_service.voice_name,
                        "voice_profile": updated_profile,
                        "tts_engine": tts_service.engine_name,
                    })

            elif msg_type in ("send_text", "text"):
                text = data.get("text", "").strip()
                if text:
                    if CURRENT_STATE != "IDLE" or (current_pipeline_task and not current_pipeline_task.done()):
                        cancel_current_pipeline()
                    current_pipeline_task = asyncio.create_task(run_text_pipeline(text))

            elif msg_type == "new_conversation":
                cancel_current_pipeline()
                current_session_id = storage.create_session()
                await broadcast({
                    "type": "conversation_cleared",
                    "session_id": current_session_id,
                })
                await set_state("IDLE")

            elif msg_type == "get_history":
                history = storage.get_recent_messages(current_session_id, limit=20)
                await websocket.send_text(
                    json.dumps({
                        "type": "history",
                        "session_id": current_session_id,
                        "messages": history,
                    })
                )

            elif msg_type in ("toggle_wake_word", "wake_word"):
                enable = data.get("enabled", False)
                if enable and not wake_word_service.is_running:
                    await asyncio.to_thread(stt_service.load_model)
                    wake_word_service.start()
                elif not enable and wake_word_service.is_running:
                    wake_word_service.stop()
                await broadcast({
                    "type": "wake_word_status",
                    "active": wake_word_service.is_running,
                })

            elif msg_type == "toggle_deep_search":
                deep_search_active = bool(data.get("enabled", True))
                storage.set_setting("deep_search", "true" if deep_search_active else "false")
                await broadcast({
                    "type": "deep_search_status",
                    "active": deep_search_active,
                })

            elif msg_type == "set_model":
                new_model = data.get("model")
                if new_model:
                    ollama_service.model = new_model
                    await broadcast({
                        "type": "model_updated",
                        "model": new_model,
                    })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
    finally:
        active_connections.discard(websocket)


# Serve built Frontend UI
DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="frontend-assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(DIST_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.app:app", host="127.0.0.1", port=8000, reload=False)
