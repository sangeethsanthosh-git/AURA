import { useState } from "react";
import { ArrowUpRightIcon, FilterSlidersIcon, SearchIcon } from "../ui/Icons";
import { useAuraRuntime } from "../../state/AuraContext";

interface AuraHubFeedProps {
  onQuickPrompt: (prompt: string) => void;
  onNewChat: () => void;
}

export function AuraHubFeed({ onQuickPrompt, onNewChat }: AuraHubFeedProps) {
  const { memories, activities, backend, voiceState } = useAuraRuntime();
  const [filterText, setFilterText] = useState("");

  const quickFeatures = [
    {
      id: "vision",
      title: "Screen & Vision AI",
      badge: "On Demand",
      description: "Ask AURA to read your active screen or inspect visual files.",
      prompt: "Read my screen and explain what is open right now.",
      icon: "👁️",
      hasWave: false,
    },
    {
      id: "voice",
      title: "Multilingual Voice Engine",
      badge: voiceState === "RECORDING" ? "Listening..." : "Push-to-Talk",
      description: "Supports Malayalam, English, Hindi, and Tamil local TTS.",
      prompt: "Speak to me in Malayalam.",
      icon: "🎙️",
      hasWave: true,
    },
    {
      id: "knowledge",
      title: "Local Knowledge & RAG",
      badge: `${memories.length} Memories`,
      description: "Local-first private document search and context retrieval.",
      prompt: "List what you remember about my preferences.",
      icon: "🧠",
      hasWave: false,
    },
    {
      id: "system",
      title: "Local AI Router",
      badge: backend,
      description: "Routes between Ollama, Groq, and custom local models.",
      prompt: "/chat explain how local smart routing works.",
      icon: "⚡",
      hasWave: false,
    },
  ];

  const filteredFeatures = quickFeatures.filter(
    (f) =>
      f.title.toLowerCase().includes(filterText.toLowerCase()) ||
      f.description.toLowerCase().includes(filterText.toLowerCase())
  );

  return (
    <section className="mail-feed-column aura-hub-column" aria-label="AURA Assistant Hub">
      {/* Search / Command Bar */}
      <div className="search-pill-container">
        <span className="search-icon-box">
          <SearchIcon />
        </span>
        <input
          type="text"
          className="search-input"
          placeholder="Search tools & commands..."
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
        />
        <button className="search-filter-button" title="New Session" type="button" onClick={onNewChat}>
          <FilterSlidersIcon />
        </button>
      </div>

      {/* Hub Cards List */}
      <div className="mail-cards-list">
        {filteredFeatures.map((item) => (
          <article
            key={item.id}
            className="mail-card hub-card"
            onClick={() => onQuickPrompt(item.prompt)}
          >
            <div className="mail-card-header">
              <div className="sender-profile">
                <div className="hub-feature-icon-box">
                  <span>{item.icon}</span>
                </div>
                <div className="sender-info">
                  <h3 className="sender-name">{item.title}</h3>
                </div>
              </div>
              <span className="expand-arrow-icon" aria-hidden="true">
                <ArrowUpRightIcon />
              </span>
            </div>

            <div className="mail-card-body">
              <div className="hub-badge-pill">{item.badge}</div>
              <p className="mail-card-preview">{item.description}</p>

              {item.hasWave && (
                <div className="audio-waveform-visualizer" aria-label="Voice audio visualizer">
                  {[4, 8, 12, 18, 22, 16, 10, 14, 20, 24, 18, 12, 8, 15, 20, 16, 10, 6, 12, 18, 14, 8, 4].map((h, i) => (
                    <span
                      key={i}
                      className="waveform-bar"
                      style={{ height: `${h}px` }}
                    />
                  ))}
                </div>
              )}
            </div>
          </article>
        ))}

        {/* Recent Activities Section */}
        {activities.length > 0 && (
          <div className="recent-activity-section">
            <h4 className="recent-activity-title">Recent Queries</h4>
            {activities.slice(0, 3).map((act, index) => (
              <div
                key={index}
                className="activity-mini-card"
                onClick={() => onQuickPrompt(act.user_message)}
              >
                <span className="activity-msg">{act.user_message}</span>
                <span className="activity-source-tag">{act.execution_source || act.intent}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
