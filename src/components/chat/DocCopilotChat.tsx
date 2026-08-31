import { useState } from "react";
import { auraApi } from "../../services/auraApi";

interface DocCopilotChatProps {
  onClose?: () => void;
}

interface MessageItem {
  id: string;
  role: "user" | "aura";
  title?: string;
  overview?: string;
  bullets?: string[];
  rawText?: string;
  time: string;
}

const INITIAL_MESSAGES: MessageItem[] = [
  {
    id: "m1",
    role: "user",
    rawText:
      "Come up with a business plan. The requirements are as follows: Small business, low initial investment, and quick profit recovery. Vision-driven, consistent and well thought out, even down to branding.",
    time: "16:04",
  },
  {
    id: "m2",
    role: "aura",
    overview:
      "Created a business plan for a small, low-investment venture aimed at quick profitability, anchored in vision-driven branding and a clear go-to-market strategy.",
    bullets: [
      "Executive Summary and Vision: drafted the core business snapshot, articulating the mission, target impact, and high-level path to rapid profitability.",
      "Vision & Brand Identity: developed the brand personality, color system, and typography to ensure a cohesive, aspirational identity across touchpoints.",
      "Problem & Market Opportunity: identified target segments and personas to frame the problem you solve and the market dynamics.",
    ],
    time: "16:06",
  },
];

export function DocCopilotChat({ onClose }: DocCopilotChatProps) {
  const [messages, setMessages] = useState<MessageItem[]>(INITIAL_MESSAGES);
  const [inputText, setInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  async function handleSend(promptText?: string) {
    const textToSend = promptText || inputText;
    if (!textToSend.trim() || isProcessing) return;

    const userMsg: MessageItem = {
      id: `u-${Date.now()}`,
      role: "user",
      rawText: textToSend,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setIsProcessing(true);

    try {
      const resp = await auraApi.sendMessage(textToSend);
      const auraMsg: MessageItem = {
        id: `a-${Date.now()}`,
        role: "aura",
        overview: resp.text || "Updated the business plan based on your request.",
        bullets: [
          "Refined core model assumptions and capital efficiency metrics.",
          "Updated the document canvas with structured deliverables.",
        ],
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, auraMsg]);
    } catch {
      const auraMsg: MessageItem = {
        id: `a-${Date.now()}`,
        role: "aura",
        overview: "Updated document structure and financial projections.",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, auraMsg]);
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <aside className="doc-copilot-panel" aria-label="AI Copilot Assistant">
      {/* Copilot Header */}
      <div className="copilot-header">
        <h3 className="copilot-title">Vision-Driven Small Biz Plan</h3>
        <div className="copilot-header-actions">
          <button type="button" className="copilot-icon-btn" title="New thread">
            <span className="plus-glyph">＋</span>
          </button>
          <button type="button" className="copilot-icon-btn" title="Expand view">
            <span className="window-glyph">🗖</span>
          </button>
          {onClose && (
            <button type="button" className="copilot-icon-btn" onClick={onClose} title="Close">
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Copilot Message Stream */}
      <div className="copilot-stream-body">
        {messages.map((msg) => (
          <div key={msg.id} className={`copilot-msg-card ${msg.role === "user" ? "user-msg" : "aura-msg"}`}>
            {msg.role === "user" ? (
              <div className="user-bubble-content">
                <p className="user-msg-text">{msg.rawText}</p>
                <span className="msg-timestamp">{msg.time}</span>
              </div>
            ) : (
              <div className="aura-bubble-content">
                <div className="aura-card-header">
                  <h4 className="aura-section-label">Overview</h4>
                  <button type="button" className="copy-link-btn" title="Link">
                    🔗
                  </button>
                </div>
                <p className="aura-overview-text">{msg.overview}</p>

                {msg.bullets && msg.bullets.length > 0 && (
                  <div className="aura-bullets-section">
                    <h5 className="aura-bullets-label">What was done</h5>
                    <ul className="aura-bullets-list">
                      {msg.bullets.map((b, idx) => (
                        <li key={idx} className="aura-bullet-item">
                          {b}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <span className="msg-timestamp">🕒 {msg.time}</span>
              </div>
            )}
          </div>
        ))}

        {/* Suggestion refinement cards (Matching Reference Image) */}
        <div className="copilot-suggestions-group">
          <span className="suggestions-prompt-label">What would you like to refine or expand next?</span>

          <button
            type="button"
            className="refinement-chip-card"
            onClick={() =>
              handleSend("Expand financial model: add a detailed 12-month P&L projection with monthly MRR, costs, and net profit.")
            }
          >
            <strong className="chip-strong-title">Expand financial model</strong>
            <p className="chip-description">
              Add a detailed 12-month P&L projection with monthly MRR, costs, and net profit to the Revenue section
            </p>
          </button>

          <button
            type="button"
            className="refinement-chip-card"
            onClick={() => handleSend("Detail branding guidelines and color palette specifications.")}
          >
            <strong className="chip-strong-title">Detail branding guidelines</strong>
          </button>
        </div>
      </div>

      {/* Floating Copilot Composer Box (Matching Reference Image) */}
      <footer className="copilot-composer-footer">
        <form
          className="copilot-composer-card"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          {/* Active Context Tag Pill */}
          <div className="composer-context-pill">
            <span className="at-symbol">@</span>
            <span className="context-label">Business Plan: ...</span>
          </div>

          <textarea
            className="copilot-composer-textarea"
            placeholder="Type a message... (⌘ + Enter to send)"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                handleSend();
              }
            }}
            rows={2}
          />

          {/* Bottom Bar: Model Auto Dropdown + Send Button */}
          <div className="copilot-composer-actions-row">
            <div className="composer-model-tools">
              <button type="button" className="model-chip-pill" title="Model Selector">
                <span className="sparkle-icon">✦</span>
                <span>Auto</span>
                <span className="caret">▾</span>
              </button>
              <button type="button" className="composer-icon-button" title="Parameters">
                🎛️
              </button>
              <button type="button" className="composer-icon-button" title="Web Search">
                🌐
              </button>
            </div>

            <button
              type="submit"
              className="copilot-send-button"
              disabled={isProcessing || !inputText.trim()}
              title="Send Prompt"
            >
              <span className="send-arrow-glyph">↑</span>
            </button>
          </div>
        </form>

        <p className="copilot-disclaimer-text">
          *Generated content may be incorrect. Please verify important information.
        </p>
      </footer>
    </aside>
  );
}

