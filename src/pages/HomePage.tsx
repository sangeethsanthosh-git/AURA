import { FormEvent, PointerEvent as ReactPointerEvent, useEffect, useRef, useState } from "react";
import { useAuraRuntime } from "../state/AuraContext";
import { auraApi } from "../services/auraApi";
import { ArrowUpIcon, MicIcon, PaperclipIcon } from "../components/ui/Icons";
import { WorkstationSidebar } from "../components/shell/WorkstationSidebar";
import { WorkstationCanvas } from "../components/studio/WorkstationCanvas";
import { WorkstationInspector } from "../components/widgets/WorkstationInspector";
import { readAppSettings, subscribeToAppSettings } from "../state/appSettings";

interface HomePageProps {
  onOpenChat?: () => void;
  initialPrompt?: string;
  onNewChat?: () => void;
  showLeftHub?: boolean;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  provider?: string;
  model?: string;
  executionTime?: number;
  spokenText?: string | null;
  sources?: ChatSource[];
  timestamp: string;
}

interface ChatSource {
  title: string;
  url: string;
  domain?: string;
}

interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  pinned?: boolean;
  archived?: boolean;
  updatedAt: number;
}

const CHAT_STORAGE_KEY = "aura.chat.sessions.v1";

function loadChatSessions(): ChatSession[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(Boolean) as ChatSession[] : [];
  } catch {
    return [];
  }
}

function saveChatSessions(sessions: ChatSession[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(sessions));
}

function extractSources(raw: Record<string, unknown> | undefined): ChatSource[] {
  const data = raw?.data;
  if (!data || typeof data !== "object") return [];
  const sources = (data as { sources?: unknown }).sources;
  if (!Array.isArray(sources)) return [];
  return sources
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const source = item as Record<string, unknown>;
      const url = String(source.url || "");
      if (!url.startsWith("http")) return null;
      return {
        title: String(source.title || source.domain || url),
        url,
        domain: source.domain ? String(source.domain) : undefined,
      };
    })
    .filter(Boolean)
    .slice(0, 4) as ChatSource[];
}

const OLLAMA_MODELS = [
  { id: "auto", label: "Auto Ollama", prefix: "" },
  { id: "nvidia-nemotron", label: "NVIDIA Nemotron", prefix: "/nvidia " },
  { id: "gemma3-1b", label: "gemma3:1b", prefix: "/ollama gemma3:1b " },
  { id: "gemma3-4b", label: "gemma3:4b", prefix: "/ollama gemma3:4b " },
  { id: "llama3-2-3b", label: "llama3.2:3b", prefix: "/ollama llama3.2:3b " },
  { id: "qwen3-4b", label: "qwen3:4b", prefix: "/ollama qwen3:4b " },
];

const SUGGESTIONS = [
  { label: "Write a first draft", prompt: "Write a professional first draft for a project kickoff announcement." },
  { label: "Get advice", prompt: "What are the best strategies for local-first privacy-oriented software design?" },
  { label: "Learn something new", prompt: "Explain how neural attention mechanisms work in simple terms." },
  { label: "Make a plan", prompt: "Create a step-by-step roadmap to build an autonomous desktop AI assistant." },
  { label: "🌦️ Check weather", prompt: "/weather Kochi" },
];

export function HomePage({ initialPrompt, showLeftHub = false, onNewChat }: HomePageProps) {
  const { backend, voiceState, refreshRuntime } = useAuraRuntime();
  const [settings, setSettings] = useState(() => readAppSettings());
  const [sessions, setSessions] = useState<ChatSession[]>(() => loadChatSessions());
  const [activeSessionId, setActiveSessionId] = useState<string>(() => {
    const first = loadChatSessions()[0];
    return first?.id || "session-1";
  });
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const found = loadChatSessions().find((session) => session.id === activeSessionId);
    return found?.messages || [];
  });
  const [inputText, setInputText] = useState(initialPrompt || "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [ollamaModelIdx, setOllamaModelIdx] = useState(0);
  const [workstationTitle, setWorkstationTitle] = useState("AURA Creative Workstation");
  const [leftPaneWidth, setLeftPaneWidth] = useState(() => readPaneWidth("aura:leftPaneWidth", 260, 220, 560));
  const [rightPaneWidth, setRightPaneWidth] = useState(() => readPaneWidth("aura:rightPaneWidth", 430, 340, 620));
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isWorkstationMode = showLeftHub;
  const userName = settings.profileName || "Alex";
  const weatherCity = settings.weatherCity || "Kochi";

  // Dynamic greeting based on current local hour
  const greeting = (() => {
    const hour = new Date().getHours();
    if (hour < 12) return `Good morning ${userName},`;
    if (hour < 17) return `Good afternoon ${userName},`;
    return `Good evening ${userName},`;
  })();
  const welcomeTimeClass = (() => {
    const hour = new Date().getHours();
    if (hour < 12) return "welcome-time-morning";
    if (hour < 17) return "welcome-time-noon";
    return "welcome-time-evening";
  })();

  useEffect(() => {
    if (messages.length > 0 && typeof messagesEndRef.current?.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isSubmitting]);

  useEffect(() => {
    const current = sessions.find((session) => session.id === activeSessionId);
    if (current) {
      setMessages(current.messages);
      setWorkstationTitle(current.title);
    }
    // Do not reload the live conversation when persistence updates sessions.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId]);

  useEffect(() => {
    const title = messages[0]?.text?.slice(0, 42) || "AURA Creative Workstation";
    setSessions((current) => {
      const next = current.some((session) => session.id === activeSessionId)
        ? current.map((session) => (
          session.id === activeSessionId
            ? { ...session, title, messages, updatedAt: Date.now() }
            : session
        ))
        : [{ id: activeSessionId, title, messages, updatedAt: Date.now() }, ...current];
      saveChatSessions(next);
      return next;
    });
  }, [activeSessionId, messages]);

  useEffect(() => {
    const sync = () => {
      const next = readAppSettings();
      setSettings(next);
      setWorkstationTitle((prev) => prev || next.profileName);
    };
    return subscribeToAppSettings(sync);
  }, []);

  async function handleSendPrompt(promptToSend?: string) {
    const rawPrompt = (promptToSend || inputText).trim();
    if (!rawPrompt || isSubmitting) return;

    let finalPrompt = rawPrompt;
    const selectedOllama = OLLAMA_MODELS[ollamaModelIdx];
    if (selectedOllama.prefix && !finalPrompt.startsWith("/")) {
      finalPrompt = `${selectedOllama.prefix}${finalPrompt}`;
    }

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      role: "user",
      text: rawPrompt,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setIsSubmitting(true);

    try {
      const response = await auraApi.sendMessage(finalPrompt);
      const assistantMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        role: "assistant",
        text: response.text || "I have processed your request.",
        provider: response.llm_provider || "Local AI",
        model: response.model || "smart-router",
        executionTime: response.execution_time,
        spokenText: response.spoken_text,
        sources: extractSources(response.raw),
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      void refreshRuntime();
    } catch {
      const fallbackMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        role: "assistant",
        text: "I am connected to your local AURA AI companion engine. Ready to help with screen inspection, voice in Malayalam/English, weather, or local computation.",
        provider: "Local Engine",
        model: "offline-ready",
        executionTime: 0.04,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleFormSubmit(e: FormEvent) {
    e.preventDefault();
    void handleSendPrompt();
  }

  function cycleOllamaModel() {
    setOllamaModelIdx((prev) => (prev + 1) % OLLAMA_MODELS.length);
  }

  function startNewChat() {
    const nextId = `session-${Date.now()}`;
    setActiveSessionId(nextId);
    setMessages([]);
    setInputText("");
    setWorkstationTitle("AURA Creative Workstation");
    onNewChat?.();
  }

  function openSession(sessionId: string) {
    const found = sessions.find((session) => session.id === sessionId);
    if (!found) return;
    setActiveSessionId(sessionId);
    setMessages(found.messages);
    setWorkstationTitle(found.title);
  }

  function pinSession(sessionId: string) {
    setSessions((current) => {
      const next = current.map((session) => session.id === sessionId ? { ...session, pinned: !session.pinned, updatedAt: Date.now() } : session);
      saveChatSessions(next);
      return next;
    });
  }

  function archiveSession(sessionId: string) {
    setSessions((current) => {
      const next = current.map((session) => session.id === sessionId ? { ...session, archived: true, updatedAt: Date.now() } : session);
      saveChatSessions(next);
      if (activeSessionId === sessionId) {
        const nextActive = next.find((session) => !session.archived);
        if (nextActive) {
          setActiveSessionId(nextActive.id);
          setMessages(nextActive.messages);
          setWorkstationTitle(nextActive.title);
        }
      }
      return next;
    });
  }

  function deleteSession(sessionId: string) {
    setSessions((current) => {
      const next = current.filter((session) => session.id !== sessionId);
      saveChatSessions(next);
      if (activeSessionId === sessionId) {
        const nextActive = next[0];
        setActiveSessionId(nextActive?.id || "session-1");
        setMessages(nextActive?.messages || []);
        setWorkstationTitle(nextActive?.title || "AURA Creative Workstation");
      }
      return next;
    });
  }

  function beginPaneResize(side: "left" | "right", event: ReactPointerEvent<HTMLButtonElement>) {
    event.preventDefault();
    const startX = event.clientX;
    const startingWidth = side === "left" ? leftPaneWidth : rightPaneWidth;

    document.body.classList.add("is-resizing-workstation");

    function updateWidth(pointerEvent: globalThis.PointerEvent) {
      const delta = pointerEvent.clientX - startX;
      const nextWidth = side === "left" ? startingWidth + delta : startingWidth - delta;
      const minWidth = side === "left" ? 220 : 340;
      const maxWidth = side === "left" ? 560 : 620;
      const clampedWidth = Math.round(Math.max(minWidth, Math.min(maxWidth, nextWidth)));

      if (side === "left") {
        setLeftPaneWidth(clampedWidth);
        localStorage.setItem("aura:leftPaneWidth", String(clampedWidth));
      } else {
        setRightPaneWidth(clampedWidth);
        localStorage.setItem("aura:rightPaneWidth", String(clampedWidth));
      }
    }

    function stopResize() {
      document.body.classList.remove("is-resizing-workstation");
      window.removeEventListener("pointermove", updateWidth);
      window.removeEventListener("pointerup", stopResize);
      window.removeEventListener("pointercancel", stopResize);
    }

    window.addEventListener("pointermove", updateWidth);
    window.addEventListener("pointerup", stopResize);
    window.addEventListener("pointercancel", stopResize);
  }

  if (isWorkstationMode) {
    return (
      <div className="workstation-root-environment" aria-label="AURA 3-pane workstation">
        <div className="workstation-app-frame">
          <div className="workstation-main-viewport">
            {showLeftHub && (
              <>
                <div className="workstation-resizable-pane workstation-resizable-pane--left" style={{ width: leftPaneWidth }}>
                  <WorkstationSidebar
                    activePage="chat"
                    onPageChange={() => undefined}
                    activeSessionTitle={workstationTitle}
                    sessions={sessions.map((session) => ({ id: session.id, title: session.title, pinned: session.pinned, archived: session.archived }))}
                    activeSessionId={activeSessionId}
                    onOpenSession={openSession}
                    onPinSession={pinSession}
                    onArchiveSession={archiveSession}
                    onDeleteSession={deleteSession}
                    onSelectSession={setWorkstationTitle}
                    onNewSession={startNewChat}
                  />
                </div>
                <button
                  type="button"
                  className="workstation-resize-handle workstation-resize-handle--left"
                  onPointerDown={(event) => beginPaneResize("left", event)}
                  title="Resize left panel"
                  aria-label="Resize left panel"
                />
              </>
            )}
            <main className="workstation-center-pane">
              <WorkstationCanvas sessionTitle={workstationTitle} />
            </main>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`aura-wallpaper-environment ${welcomeTimeClass}`} aria-label="AURA Interactive Studio">
      {/* 1. SCENIC NATURE WALLPAPER BACKDROP (Matching Reference Image) */}
      <div className="scenic-nature-wallpaper-layer" />

      {/* 2. MAIN FLOATING APPLICATION FRAME CANVAS */}
      <div className="floating-browser-window-frame">
        {/* Top Browser / Window Tab Bar */}
        <header className="browser-top-window-bar">
          <div className="browser-tab-cluster">
            <div className="browser-active-tab">
              <span className="tab-gem-glyph">✦</span>
              <span className="tab-label-text">
                {messages.length === 0 ? "New tab" : "AURA Conversation"}
              </span>
              <button
                type="button"
                className="tab-close-btn"
                onClick={startNewChat}
                title="New Session"
              >
                ×
              </button>
            </div>
            <button
              type="button"
              className="browser-new-tab-plus"
              onClick={startNewChat}
              title="New Chat Session"
            >
              +
            </button>
          </div>

          <div className="browser-address-bar">
            <span className="address-search-icon">🔍</span>
            <span className="address-url-text">aura://studio/search-and-chat</span>
          </div>

          <div className="browser-right-actions">
            <div className="engine-status-pill-mini" title={`Local AI Engine: ${backend}`}>
              <span
                className="engine-status-dot-mini"
                style={{ background: backend === "READY" ? "#10b981" : "#f59e0b" }}
              />
              <span>{backend}</span>
            </div>
            <div className="browser-user-avatar-circle" title="Alex (Active User)">
              <span>👤</span>
            </div>
            <button
              type="button"
              className="browser-settings-cog-btn"
              onClick={startNewChat}
              title="Settings & Reset"
            >
              ⚙
            </button>
          </div>
        </header>

        {/* 3. MAIN CONTENT AREA */}
        <main className="browser-canvas-body">
          {/* VIEW A: CALM WELCOME FRONT (When no conversation is active) */}
          {messages.length === 0 ? (
            <div className="welcome-front-center-stage">
              {/* Centered Editorial Greeting (Matching Reference Image) */}
              <div className="welcome-greeting-headline-box">
                <h1 className="welcome-greeting-line-1">{greeting}</h1>
                <h2 className="welcome-greeting-line-2">How can I help you today?</h2>
              </div>

              {/* Floating Pill Capsule Composer */}
              <form className="welcome-capsule-composer-card" onSubmit={handleFormSubmit}>
                <input
                  type="text"
                  className="capsule-composer-input"
                  placeholder="Type a link or ask anything..."
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  autoFocus
                />

                <div className="capsule-bottom-controls-row">
                  {/* Model Switcher Dropdown Button */}
                  <button
                    type="button"
                    className="capsule-model-selector-btn"
                    onClick={cycleOllamaModel}
                    title="Cycle model preference. Use /wiki, /nvidia, /groq, /hug, or /web for provider routing."
                  >
                    <span className="model-sparkle-icon">🔮</span>
                    <span className="model-name-label">{OLLAMA_MODELS[ollamaModelIdx].label}</span>
                    <span className="model-chevron-down">▾</span>
                  </button>

                  <div className="capsule-right-tools">
                  <button
                      type="button"
                      className="capsule-tool-icon-btn"
                      onClick={() => setInputText((prev) => (prev ? `${prev} /weather ` : "/weather "))}
                      title="Check weather"
                    >
                      <PaperclipIcon />
                    </button>
                    <button
                      type="button"
                      className={`capsule-mic-btn ${voiceState === "RECORDING" ? "recording" : ""}`}
                      onClick={() => setInputText("Speak in Malayalam: എനിക്ക് ഇന്നത്തെ പ്രധാന വിവരങ്ങൾ പറഞ്ഞു തരൂ")}
                      title="Voice input in Malayalam or English"
                    >
                      <MicIcon />
                    </button>
                    <button
                      type="submit"
                      className="capsule-send-btn"
                      disabled={!inputText.trim() || isSubmitting}
                      title="Send message"
                    >
                      <ArrowUpIcon />
                    </button>
                  </div>
                </div>
              </form>

              {/* Suggestion Chips Row (Matching Reference Image) */}
              <div className="welcome-suggestions-strip" role="list" aria-label="Suggested Prompts">
                {SUGGESTIONS.map((sug, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="welcome-suggestion-pill"
                    onClick={() => {
                      setInputText(sug.prompt);
                      void handleSendPrompt(sug.prompt);
                    }}
                  >
                    {sug.label}
                  </button>
                ))}
              </div>

            </div>
          ) : (
            /* VIEW B: INTERACTIVE CONVERSATION CANVAS (Gemini / Antigravity Interaction) */
            <div className="interactive-chat-session-stage">
              {/* Chat Messages Stream */}
              <div className="chat-messages-scroll-area">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`chat-interaction-row ${msg.role === "user" ? "user-turn" : "assistant-turn"}`}
                  >
                    {msg.role === "assistant" && (
                      <div className="assistant-avatar-column">
                        <div className="assistant-gem-avatar">✦</div>
                      </div>
                    )}

                    <div className="message-content-bubble">
                      <div className="message-header-meta">
                        <span className="sender-name">
                          {msg.role === "user" ? "You" : "AURA"}
                        </span>
                        {msg.provider && (
                          <span className="message-provider-tag">
                            {msg.provider} {msg.model ? `• ${msg.model}` : ""}{" "}
                            {msg.executionTime ? `(${msg.executionTime}s)` : ""}
                          </span>
                        )}
                        <span className="message-time-label">{msg.timestamp}</span>
                      </div>

                      <div className="message-body-text">{msg.text}</div>

                      {msg.sources && msg.sources.length > 0 && (
                        <div className="message-source-strip" aria-label="Response sources">
                          {msg.sources.map((source) => {
                            const hostname = new URL(source.url).hostname;
                            return (
                              <a key={source.url} className="message-source-card" href={source.url} target="_blank" rel="noreferrer">
                                <span>{source.domain || hostname}</span>
                                <strong>{source.title}</strong>
                              </a>
                            );
                          })}
                        </div>
                      )}

                      {msg.spokenText && (
                        <div className="message-audio-tts-bar">
                          <span className="tts-icon">🔊</span>
                          <span className="tts-text">{msg.spokenText}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {isSubmitting && (
                  <div className="chat-interaction-row assistant-turn">
                    <div className="assistant-avatar-column">
                      <div className="assistant-gem-avatar pulsating">✦</div>
                    </div>
                    <div className="message-content-bubble thinking-bubble">
                      <span className="thinking-dot" />
                      <span className="thinking-dot" />
                      <span className="thinking-dot" />
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Pinned Bottom Interactive Floating Composer */}
              <div className="pinned-chat-composer-wrap">
                <form className="pinned-chat-composer-form" onSubmit={handleFormSubmit}>
                  <input
                    type="text"
                    className="pinned-input-field"
                    placeholder="Ask a follow-up or command (/weather)..."
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    disabled={isSubmitting}
                    autoFocus
                  />

                  <div className="pinned-controls-cluster">
                    <button
                      type="button"
                      className="pinned-router-chip"
                      onClick={cycleOllamaModel}
                      title="Cycle model preference. Provider commands: /wiki, /nvidia, /groq, /hug, /web."
                    >
                      {OLLAMA_MODELS[ollamaModelIdx].label}
                    </button>
                    <button
                      type="button"
                      className="pinned-tool-btn"
                      onClick={() => setInputText((prev) => (prev ? `${prev} /weather ` : "/weather "))}
                      title="Check weather"
                    >
                      <PaperclipIcon />
                    </button>
                    <button
                      type="button"
                      className={`pinned-tool-btn ${voiceState === "RECORDING" ? "recording" : ""}`}
                      onClick={() => setInputText("Speak in Malayalam: എനിക്ക് കൂടുതൽ പറഞ്ഞു തരൂ")}
                      title="Voice input"
                    >
                      <MicIcon />
                    </button>
                    <button
                      type="submit"
                      className="pinned-send-submit-btn"
                      disabled={!inputText.trim() || isSubmitting}
                      title="Send"
                    >
                      <ArrowUpIcon />
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

function readPaneWidth(key: string, fallback: number, min: number, max: number) {
  if (typeof window === "undefined") {
    return fallback;
  }
  const saved = Number(window.localStorage.getItem(key));
  if (!Number.isFinite(saved)) {
    return fallback;
  }
  return Math.max(min, Math.min(max, saved));
}
