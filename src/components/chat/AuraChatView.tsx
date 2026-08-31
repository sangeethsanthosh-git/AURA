import { FormEvent, useState, useRef, useEffect } from "react";
import { WelcomeScreen } from "./WelcomeScreen";
import {
  ArrowUpIcon,
  CopyIcon,
  MicIcon,
  PaperclipIcon,
  SwitchArrowsIcon,
} from "../ui/Icons";
import { useAuraRuntime } from "../../state/AuraContext";
import { auraApi, AuraResponse } from "../../services/auraApi";

export interface ChatMessageItem {
  id: string;
  role: "user" | "aura" | "system";
  text: string;
  response?: AuraResponse;
  timestamp: string;
}

export function AuraChatView({
  initialPrompt,
  onResetPrompt,
}: {
  initialPrompt?: string;
  onResetPrompt?: () => void;
}) {
  const { backend, voiceState, refreshRuntime } = useAuraRuntime();
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [inputText, setInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const chatStreamEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (initialPrompt) {
      void handleSendMessage(initialPrompt);
      onResetPrompt?.();
    }
  }, [initialPrompt]);

  useEffect(() => {
    chatStreamEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  async function handleSendMessage(textToSend?: string) {
    const raw = textToSend || inputText;
    const clean = raw.trim();
    if (!clean || isProcessing) return;

    const userMsg: ChatMessageItem = {
      id: crypto.randomUUID(),
      role: "user",
      text: clean,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputText("");
    setIsProcessing(true);

    try {
      if (backend === "READY") {
        const res = await auraApi.sendMessage(clean);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "aura",
            text: res.text,
            response: res,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ]);
        await refreshRuntime();
      } else {
        // Fallback demo response if backend is starting or offline
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "aura",
              text: `AURA processed "${clean}". Backend status is currently ${backend}. Ollama and local SmartRouter services are ready for local processing.`,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            },
          ]);
          setIsProcessing(false);
        }, 500);
        return;
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "system",
          text: err instanceof Error ? err.message : "Error connecting to AURA local engine.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  }

  function handleFormSubmit(e: FormEvent) {
    e.preventDefault();
    void handleSendMessage();
  }

  async function handleVoiceClick() {
    try {
      if (voiceState === "RECORDING") {
        const res = await auraApi.stopVoice();
        if (res.text) {
          setInputText(res.text);
        }
      } else {
        await auraApi.startVoice();
      }
      await refreshRuntime();
    } catch {
      // Voice error handling
    }
  }

  function handleCopyText(text: string, id: string) {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  function clearChat() {
    setMessages([]);
  }

  return (
    <main className="mail-reader-pane aura-chat-pane" aria-label="AURA Assistant Interface">
      {/* Top Bar with Clear / New Session */}
      <div className="reader-topbar">
        <div className="chat-top-status">
          <span className="chat-aura-badge">AURA Multilingual Assistant</span>
          {backend === "READY" && <span className="active-tag">Online</span>}
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            className="clear-chat-btn"
            onClick={clearChat}
            title="Start New Conversation"
          >
            + New Chat
          </button>
        )}
      </div>

      {/* Main Center Area: Gemini/ChatGPT Welcome Screen or Message Stream */}
      {messages.length === 0 ? (
        <div className="chat-empty-state-viewport">
          <WelcomeScreen
            userName="User"
            backendState={backend}
            onSelectPrompt={(prompt) => void handleSendMessage(prompt)}
          />
        </div>
      ) : (
        <div className="chat-messages-stream" aria-live="polite">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`chat-bubble-container ${msg.role === "user" ? "user-bubble-wrap" : "aura-bubble-wrap"}`}
            >
              {msg.role !== "user" && (
                <div className="aura-avatar-mini" title="AURA">
                  <div className="mini-orb-dot" />
                </div>
              )}

              <div className={`chat-message-bubble ${msg.role === "user" ? "bubble-user" : "bubble-aura"}`}>
                <div className="bubble-header-row">
                  <span className="bubble-author-name">
                    {msg.role === "user" ? "You" : msg.role === "system" ? "System" : "AURA"}
                  </span>
                  <span className="bubble-time">{msg.timestamp}</span>
                </div>

                <div className="bubble-text-content">
                  <p>{msg.text}</p>
                </div>

                {/* Metadata & Actions for AURA responses */}
                {msg.response && (
                  <div className="bubble-metadata-footer">
                    <span className="meta-pill">Provider: {msg.response.llm_provider || "Local"}</span>
                    <span className="meta-pill">Model: {msg.response.model || "AURA-ASUS"}</span>
                    {msg.response.execution_time > 0 && (
                      <span className="meta-pill">{msg.response.execution_time.toFixed(2)}s</span>
                    )}
                    <button
                      type="button"
                      className="copy-btn-mini"
                      onClick={() => handleCopyText(msg.text, msg.id)}
                      title="Copy response"
                    >
                      {copiedId === msg.id ? "✓ Copied" : <CopyIcon />}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {isProcessing && (
            <div className="chat-bubble-container aura-bubble-wrap">
              <div className="aura-avatar-mini">
                <div className="mini-orb-dot pulsing" />
              </div>
              <div className="chat-message-bubble bubble-aura thinking-bubble">
                <span className="thinking-dots">AURA is thinking</span>
                <span className="dot-pulse" />
              </div>
            </div>
          )}

          <div ref={chatStreamEndRef} />
        </div>
      )}

      {/* Reply / Chat Composer */}
      <footer className="reply-composer-footer">
        <form className="reply-composer-pill" onSubmit={handleFormSubmit}>
          <input
            type="text"
            className="reply-composer-input"
            placeholder={
              messages.length === 0
                ? "Ask AURA anything, search web, or type a command..."
                : "Type your message..."
            }
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isProcessing}
          />
          <div className="reply-composer-actions">
            <button
              type="button"
              className="composer-icon-button"
              title="Attach File or Vision Command (/screen, /file)"
              onClick={() => setInputText("/screen ")}
            >
              <PaperclipIcon />
            </button>
            <button
              type="button"
              className="composer-icon-button"
              title="Switch Router Mode (/groq, /hf, /ollama)"
              onClick={() => {
                setInputText((prev) =>
                  prev.startsWith("/groq ") ? "/chat " : "/groq "
                );
              }}
            >
              <SwitchArrowsIcon />
            </button>
            <button
              type="button"
              className={`composer-icon-button ${voiceState === "RECORDING" ? "recording" : ""}`}
              title={voiceState === "RECORDING" ? "Stop Recording" : "Voice Input (Malayalam/English)"}
              onClick={handleVoiceClick}
            >
              <MicIcon />
            </button>
            <button
              type="submit"
              className="composer-send-button"
              title="Send message"
              disabled={isProcessing || !inputText.trim()}
            >
              <ArrowUpIcon />
            </button>
          </div>
        </form>
      </footer>
    </main>
  );
}

