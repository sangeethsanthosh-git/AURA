import { useEffect, useMemo, useState } from "react";
import { PageId } from "./AppShell";
import { useAuraRuntime } from "../../state/AuraContext";
import { SearchIcon } from "../ui/Icons";
import { readAppSettings, subscribeToAppSettings } from "../../state/appSettings";

export interface ChatSessionSummary {
  id: string;
  title: string;
  pinned?: boolean;
  archived?: boolean;
}

interface WorkstationSidebarProps {
  activePage: PageId;
  onPageChange: (page: PageId) => void;
  onSelectSession?: (sessionTitle: string) => void;
  activeSessionTitle?: string;
  onNewSession?: () => void;
  sessions?: ChatSessionSummary[];
  activeSessionId?: string;
  onOpenSession?: (sessionId: string) => void;
  onPinSession?: (sessionId: string) => void;
  onArchiveSession?: (sessionId: string) => void;
  onDeleteSession?: (sessionId: string) => void;
}

export function WorkstationSidebar({
  onSelectSession,
  activeSessionTitle = "AURA Creative Workstation",
  onNewSession,
  sessions,
  activeSessionId,
  onOpenSession,
  onPinSession,
  onArchiveSession,
  onDeleteSession,
}: WorkstationSidebarProps) {
  const { backend, memories } = useAuraRuntime();
  const [search, setSearch] = useState("");
  const [menuOpen, setMenuOpen] = useState<string | null>(null);
  const [weatherCity, setWeatherCity] = useState(() => readAppSettings().weatherCity || "Kochi");
  const shortcuts = useMemo(() => [
    { label: "Screen", prompt: "/screen read my active window" },
    { label: "Weather", prompt: `/weather ${weatherCity || "Kochi"}` },
    { label: "Wikipedia", prompt: "/wiki Taj Mahal" },
    { label: "Web", prompt: "/web latest AI news" },
  ], [weatherCity]);

  useEffect(() => subscribeToAppSettings(() => setWeatherCity(readAppSettings().weatherCity || "Kochi")), []);
  const visibleChats = useMemo(() => {
    const source = sessions || [];
    const clean = search.toLowerCase();
    return source
      .filter((chat) => !chat.archived)
      .filter((chat) => chat.title.toLowerCase().includes(clean))
      .sort((a, b) => Number(Boolean(b.pinned)) - Number(Boolean(a.pinned)));
  }, [search, sessions]);

  return (
    <aside className="cgpt-sidebar" aria-label="Chat history">
      <div className="cgpt-sidebar-top">
        <button type="button" className="cgpt-new-chat" onClick={onNewSession}>New chat</button>
        <label className="cgpt-sidebar-search">
          <SearchIcon />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search chats" />
        </label>
      </div>

      <div className="cgpt-shortcuts">
        {shortcuts.map((shortcut) => (
          <button key={shortcut.label} type="button" onClick={() => onSelectSession?.(shortcut.prompt)}>
            {shortcut.label}
          </button>
        ))}
      </div>

      <div className="cgpt-chat-list">
        <span>Chats</span>
        {visibleChats.map((chat) => (
          <div key={chat.id} className={`cgpt-chat-row ${chat.id === activeSessionId ? "active" : ""}`}>
            <button type="button" className="cgpt-chat-row-main" onClick={() => onOpenSession?.(chat.id)}>
              {chat.pinned && <span className="cgpt-chat-pin">📌</span>}
              {chat.title}
            </button>
            <button type="button" className="cgpt-chat-row-menu" onClick={() => setMenuOpen((current) => current === chat.id ? null : chat.id)} title="Chat options">⋯</button>
            {menuOpen === chat.id && (
              <div className="cgpt-chat-menu">
                <button type="button" onClick={() => { onPinSession?.(chat.id); setMenuOpen(null); }}>Pin</button>
                <button type="button" onClick={() => { onArchiveSession?.(chat.id); setMenuOpen(null); }}>Archive</button>
                <button type="button" onClick={() => { onDeleteSession?.(chat.id); setMenuOpen(null); }}>Delete</button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="cgpt-sidebar-status">
        <span className={backend === "READY" ? "ready" : ""} />
        <div>
          <strong>Local {backend}</strong>
          <small>{memories.length} memories</small>
        </div>
      </div>
    </aside>
  );
}
