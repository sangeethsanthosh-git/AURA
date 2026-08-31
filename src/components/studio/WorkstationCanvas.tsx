import { FormEvent, useEffect, useRef, useState } from "react";
import { auraApi, WebSearchResult } from "../../services/auraApi";
import { useAuraRuntime } from "../../state/AuraContext";
import { ArrowUpIcon, MicIcon, PaperclipIcon, SearchIcon } from "../ui/Icons";

interface WorkstationCanvasProps {
  sessionTitle?: string;
}

interface ChatMsg {
  id: string;
  role: "user" | "aura";
  text: string;
  provider?: string;
  model?: string;
  sources?: WebSearchResult[];
}

const MODEL_MODES = [
  { label: "Auto", prefix: "" },
  { label: "Ollama", prefix: "/ollama " },
  { label: "NVIDIA", prefix: "/nvidia " },
  { label: "Groq", prefix: "/groq " },
  { label: "Hugging Face", prefix: "/hf " },
];

const STARTERS = [
  "Explain this project pipeline",
  "/screen read my active window",
  "/weather Kochi",
  "/wiki Taj Mahal",
];

function extractSources(raw: Record<string, unknown> | undefined): WebSearchResult[] {
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
        domain: String(source.domain || new URL(url).hostname),
        snippet: String(source.snippet || ""),
      };
    })
    .filter(Boolean)
    .slice(0, 4) as WebSearchResult[];
}

export function WorkstationCanvas({ sessionTitle = "New chat" }: WorkstationCanvasProps) {
  const { voiceState, refreshRuntime } = useAuraRuntime();
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [inputText, setInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [modeIndex, setModeIndex] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof messagesEndRef.current?.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isProcessing]);

  async function sendPrompt(promptOverride?: string) {
    let prompt = (promptOverride || inputText).trim();
    if (!prompt || isProcessing) return;

    const mode = MODEL_MODES[modeIndex];
    const userText = prompt;
    if (mode.prefix && !prompt.startsWith("/")) {
      prompt = `${mode.prefix}${prompt}`;
    }

    setMessages((prev) => [...prev, { id: `u-${Date.now()}`, role: "user", text: userText }]);
    setInputText("");
    setIsProcessing(true);

    try {
      const response = await auraApi.sendMessage(prompt);
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: "aura",
          text: response.text || "Done.",
          provider: response.llm_provider || response.execution_source || "AURA",
          model: response.model || "router",
          sources: extractSources(response.raw),
        },
      ]);
      void refreshRuntime();
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: "aura",
          text: "I could not reach the local AURA runtime for that request.",
          provider: "Local runtime",
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void sendPrompt();
  }

  return (
    <section className="cgpt-workspace" aria-label="AURA chat workspace">
      <header className="cgpt-topbar">
        <button type="button" className="cgpt-model-pill" onClick={() => setModeIndex((prev) => (prev + 1) % MODEL_MODES.length)}>
          {MODEL_MODES[modeIndex].label}
        </button>
        <span>{sessionTitle}</span>
      </header>

      <div className="cgpt-thread">
        {messages.length === 0 ? (
          <div className="cgpt-empty">
            <h1>How can I help?</h1>
            <p>Ask normally, or use /screen, /wiki, /weather, /web, /nvidia, /groq, /hug, and /ollama.</p>
            <div className="cgpt-starters">
              {STARTERS.map((starter) => (
                <button key={starter} type="button" onClick={() => void sendPrompt(starter)}>
                  {starter}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <article key={message.id} className={`cgpt-message ${message.role === "user" ? "cgpt-message-user" : "cgpt-message-aura"}`}>
              <div className="cgpt-avatar">{message.role === "user" ? "You" : "A"}</div>
              <div className="cgpt-message-body">
                <div className="cgpt-message-name">
                  {message.role === "user" ? "You" : "AURA"}
                  {message.provider && <span>{message.provider}{message.model ? ` / ${message.model}` : ""}</span>}
                </div>
                <p>{message.text}</p>
                {message.sources && message.sources.length > 0 && (
                  <div className="cgpt-sources">
                    {message.sources.map((source) => (
                      <a key={source.url} href={source.url} target="_blank" rel="noreferrer">
                        <strong>{source.title}</strong>
                        <span>{source.domain}</span>
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </article>
          ))
        )}
        {isProcessing && (
          <article className="cgpt-message cgpt-message-aura">
            <div className="cgpt-avatar">A</div>
            <div className="cgpt-message-body">
              <div className="cgpt-thinking"><i /><i /><i /></div>
            </div>
          </article>
        )}
        <div ref={messagesEndRef} />
      </div>

      <footer className="cgpt-composer-wrap">
        <form className="cgpt-composer welcome-style-composer" onSubmit={handleSubmit}>
          <textarea
            value={inputText}
            onChange={(event) => setInputText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void sendPrompt();
              }
            }}
            placeholder="Message AURA..."
            rows={1}
          />
          <button
            type="button"
            className="cgpt-model-pill cgpt-model-pill--composer"
            onClick={() => setModeIndex((prev) => (prev + 1) % MODEL_MODES.length)}
            title="Cycle model router"
          >
            {MODEL_MODES[modeIndex].label}
          </button>
          <div className="cgpt-composer-actions">
            <button type="button" title="Attach file"><PaperclipIcon /></button>
            <button type="button" title="Web search" onClick={() => setInputText((prev) => (prev ? `/web ${prev}` : "/web "))}><SearchIcon /></button>
            <button type="button" className={voiceState === "RECORDING" ? "active" : ""} title="Voice"><MicIcon /></button>
            <button type="submit" className="cgpt-send" disabled={!inputText.trim() || isProcessing} title="Send"><ArrowUpIcon /></button>
          </div>
        </form>
      </footer>
    </section>
  );
}
