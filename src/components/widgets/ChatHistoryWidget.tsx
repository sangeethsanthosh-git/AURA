import { useState } from "react";
import { useAuraRuntime } from "../../state/AuraContext";

interface ChatHistoryItem {
  id: string;
  title: string;
  preview: string;
  time: string;
  avatars: string[];
  imageUrl?: string;
  checked?: boolean;
}

const DEFAULT_HISTORY: ChatHistoryItem[] = [
  {
    id: "1",
    title: "Visual exploration",
    preview: "Exploring visual styles, moods, a...",
    time: "2h ago",
    avatars: ["👩‍🦰", "🧔"],
    checked: false,
  },
  {
    id: "2",
    title: "Image generation",
    preview: "Creating a futuristic portrait usin...",
    time: "3h ago",
    avatars: ["👩‍🦱"],
    imageUrl: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&auto=format&fit=crop&q=80",
    checked: false,
  },
  {
    id: "3",
    title: "Team session",
    preview: "Collaborative prompt editing and...",
    time: "3h ago",
    avatars: ["👱‍♀️", "👨‍🦱", "👩‍🦳"],
    checked: false,
  },
  {
    id: "4",
    title: "Visualisation",
    preview: "Creating images from text prom...",
    time: "5h ago",
    avatars: ["👨‍💼"],
    checked: false,
  },
];

interface ChatHistoryWidgetProps {
  onSelectChat?: (prompt: string) => void;
  onNewChat?: () => void;
}

export function ChatHistoryWidget({ onSelectChat, onNewChat }: ChatHistoryWidgetProps) {
  const { activities } = useAuraRuntime();
  const [searchQuery, setSearchQuery] = useState("");
  const [history, setHistory] = useState<ChatHistoryItem[]>(DEFAULT_HISTORY);
  const [selectedId, setSelectedId] = useState<string>("2");

  const filtered = history.filter(
    (item) =>
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.preview.toLowerCase().includes(searchQuery.toLowerCase())
  );

  function toggleCheck(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    setHistory((prev) =>
      prev.map((item) => (item.id === id ? { ...item, checked: !item.checked } : item))
    );
  }

  function handleSelect(item: ChatHistoryItem) {
    setSelectedId(item.id);
    onSelectChat?.(item.title);
  }

  return (
    <aside className="seto-chat-history-widget" aria-label="Chat History">
      {/* Header */}
      <div className="seto-history-header">
        <h3 className="seto-history-title">Chat history</h3>
        <button type="button" className="seto-history-filter-btn" title="View options">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1.5" />
            <rect x="14" y="3" width="7" height="7" rx="1.5" />
            <rect x="14" y="14" width="7" height="7" rx="1.5" />
            <rect x="3" y="14" width="7" height="7" rx="1.5" />
          </svg>
        </button>
      </div>

      {/* Search Bar */}
      <div className="seto-history-search">
        <span className="search-icon">🔍</span>
        <input
          type="text"
          placeholder="Search..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="seto-history-search-input"
        />
      </div>

      {/* History Items List */}
      <div className="seto-history-list">
        {filtered.map((item) => {
          const isSelected = selectedId === item.id;
          return (
            <article
              key={item.id}
              className={`seto-history-item ${isSelected ? "selected" : ""}`}
              onClick={() => handleSelect(item)}
            >
              <div className="seto-item-top-row">
                <div
                  className={`seto-checkbox ${item.checked ? "checked" : ""}`}
                  onClick={(e) => toggleCheck(item.id, e)}
                >
                  {item.checked && "✓"}
                </div>
                <div className="seto-item-text-group">
                  <h4 className="seto-item-title">{item.title}</h4>
                  <p className="seto-item-preview">{item.preview}</p>
                </div>
              </div>

              {/* Rich Visual Image Thumbnail (Matching reference image) */}
              {item.imageUrl && (
                <div className="seto-item-image-preview">
                  <div className="seto-item-image-silhouette">
                    <span className="silhouette-icon">👤</span>
                  </div>
                </div>
              )}

              {/* Bottom Meta: Avatars & Timestamp */}
              <div className="seto-item-bottom-meta">
                <div className="seto-avatar-stack">
                  {item.avatars.map((av, idx) => (
                    <span key={idx} className="seto-avatar-bubble">
                      {av}
                    </span>
                  ))}
                </div>
                <span className="seto-item-time">{item.time}</span>
              </div>
            </article>
          );
        })}

        {/* Dynamic Recent System Activities */}
        {activities.slice(0, 2).map((act, i) => (
          <article
            key={`dyn-${i}`}
            className="seto-history-item"
            onClick={() => onSelectChat?.(act.user_message)}
          >
            <div className="seto-item-top-row">
              <div className="seto-checkbox" />
              <div className="seto-item-text-group">
                <h4 className="seto-item-title">{act.intent || "Quick Query"}</h4>
                <p className="seto-item-preview">{act.user_message}</p>
              </div>
            </div>
            <div className="seto-item-bottom-meta">
              <span className="seto-avatar-bubble">⚡</span>
              <span className="seto-item-time">just now</span>
            </div>
          </article>
        ))}
      </div>

      {/* Bottom Action Button: Solid Black "Create new chat" */}
      <div className="seto-history-footer">
        <button
          type="button"
          className="seto-create-chat-btn"
          onClick={onNewChat}
          title="Create New Chat"
        >
          Create new chat
        </button>
      </div>
    </aside>
  );
}

