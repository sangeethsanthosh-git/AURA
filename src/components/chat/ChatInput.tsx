import { FormEvent, useState } from "react";
import { ArrowUpIcon, MicIcon, PaperclipIcon } from "../ui/Icons";

export function ChatInput({
  disabled,
  onSend,
}: {
  disabled?: boolean;
  onSend: (message: string) => void;
}) {
  const [message, setMessage] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    const clean = message.trim();
    if (!clean) return;
    onSend(clean);
    setMessage("");
  }

  return (
    <form className="seto-studio-composer" onSubmit={submit}>
      {/* Text Input Row */}
      <div className="seto-composer-input-row">
        <input
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="✦ Initiate a query or send a command to the AI..."
          disabled={disabled}
          className="seto-composer-input"
        />
      </div>

      {/* Bottom Tools & Action Row (Matching Reference Image) */}
      <div className="seto-composer-bottom-bar">
        <div className="seto-composer-tools-left">
          <button
            type="button"
            className="seto-tool-pill-btn"
            title="Attach file or image"
          >
            <PaperclipIcon />
            <span>Attach</span>
          </button>
          <button
            type="button"
            className="seto-tool-pill-btn"
            title="Model & Prompt Settings"
          >
            <span>⚙️</span>
            <span>Settings</span>
          </button>
          <button
            type="button"
            className="seto-tool-pill-btn"
            title="Generation Options"
          >
            <span>🎛️</span>
            <span>Options</span>
          </button>
        </div>

        <div className="seto-composer-actions-right">
          <button
            type="button"
            className="seto-mic-btn"
            title="Voice input"
          >
            <MicIcon />
          </button>
          <button
            type="submit"
            className="seto-send-btn"
            disabled={disabled || !message.trim()}
            title="Send query"
          >
            <ArrowUpIcon />
          </button>
        </div>
      </div>
    </form>
  );
}
