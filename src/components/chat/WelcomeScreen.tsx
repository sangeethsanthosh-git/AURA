import { AuraOrb } from "../AuraOrb";
import { BackendState } from "../../services/auraApi";

interface WelcomeScreenProps {
  userName?: string;
  backendState?: BackendState;
  onSelectPrompt: (prompt: string) => void;
}

const promptSuggestions = [
  {
    icon: "🔍",
    label: "Google & Web Search",
    prompt: "Search the web for the latest breakthroughs in AI agents.",
  },
  {
    icon: "🌦️",
    label: "Check Weather",
    prompt: "What is the weather forecast for today?",
  },
  {
    icon: "🎵",
    label: "Music & Audio",
    prompt: "Play some relaxing synthwave background music.",
  },
  {
    icon: "👁️",
    label: "Read Screen Vision",
    prompt: "Read my screen and summarize what is visible.",
  },
  {
    icon: "🌐",
    label: "Multilingual Voice",
    prompt: "Speak to me in Malayalam about today's tasks.",
  },
  {
    icon: "🧠",
    label: "Local Knowledge Base",
    prompt: "Summarize my active memories and recent notes.",
  },
];

export function WelcomeScreen({
  userName = "User",
  backendState = "READY",
  onSelectPrompt,
}: WelcomeScreenProps) {
  return (
    <div className="welcome-screen-container" aria-label="Welcome screen">
      <div className="welcome-orb-wrapper">
        <AuraOrb state={backendState === "READY" ? "IDLE" : backendState} size={110} />
      </div>

      <div className="welcome-header">
        <h1 className="welcome-title">
          <span className="welcome-gradient-text">Hello, {userName}</span>
        </h1>
        <p className="welcome-subtitle">
          How can I assist you today? Ask anything, control media, or explore your local workspace.
        </p>
      </div>

      <div className="welcome-suggestions-grid">
        {promptSuggestions.map((item, idx) => (
          <button
            key={idx}
            type="button"
            className="suggestion-chip-card"
            onClick={() => onSelectPrompt(item.prompt)}
          >
            <span className="suggestion-icon">{item.icon}</span>
            <div className="suggestion-text">
              <strong className="suggestion-label">{item.label}</strong>
              <span className="suggestion-prompt">{item.prompt}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
