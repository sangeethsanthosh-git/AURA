import { ReactNode } from "react";
import { useAuraRuntime } from "../../state/AuraContext";
import { StatusPill } from "../ui/StatusPill";

export type PageId = "home" | "chat" | "tasks" | "knowledge" | "memory" | "activity" | "vision" | "voice" | "settings";

const pages: Array<{ id: PageId; label: string; mark: string }> = [
  { id: "home", label: "Home", mark: "A" },
  { id: "chat", label: "Chat", mark: "C" },
  { id: "tasks", label: "Tasks", mark: "T" },
  { id: "knowledge", label: "Knowledge", mark: "K" },
  { id: "memory", label: "Memory", mark: "M" },
  { id: "activity", label: "Activity", mark: "L" },
  { id: "vision", label: "Vision", mark: "V" },
  { id: "voice", label: "Voice", mark: "S" },
  { id: "settings", label: "Settings", mark: "G" },
];

export function AppShell({ page, onPageChange, children }: { page: PageId; onPageChange: (page: PageId) => void; children: ReactNode }) {
  const { backend, voiceState } = useAuraRuntime();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-orb" aria-hidden="true" />
          <div>
            <strong>AURA</strong>
            <span>ASUS V1</span>
          </div>
        </div>
        <nav aria-label="Primary">
          {pages.map((item) => (
            <button className="nav-button" data-active={page === item.id} key={item.id} onClick={() => onPageChange(item.id)}>
              <span aria-hidden="true">{item.mark}</span>
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <section className="workspace">
        <header className="topbar">
          <div className="drag-region">
            <span>AURA is local-first</span>
          </div>
          <div className="privacy-strip">
            <StatusPill label="Backend" state={backend} tone={backend === "READY" ? "good" : backend === "STARTING" ? "warn" : "bad"} />
            <StatusPill label="Mic" state={voiceState} tone={voiceState === "RECORDING" ? "warn" : "neutral"} />
            <StatusPill label="Vision" state="On demand" tone="neutral" />
          </div>
          <div className="window-controls">
            <button aria-label="Minimize" onClick={() => window.aura?.window.minimize()}>-</button>
            <button aria-label="Maximize" onClick={() => window.aura?.window.maximize()}>□</button>
            <button aria-label="Close" onClick={() => window.aura?.window.close()}>×</button>
          </div>
        </header>
        <main className="page-frame">{children}</main>
      </section>
    </div>
  );
}
