import { useState } from "react";
import { PageId } from "./AppShell";

interface SetoSidebarProps {
  activePage: PageId;
  onPageChange: (page: PageId) => void;
  onNewChat?: () => void;
}

export function SetoSidebar({ activePage, onPageChange, onNewChat }: SetoSidebarProps) {
  const [activeItem, setActiveItem] = useState<string>("home");
  const [aiToolsOpen, setAiToolsOpen] = useState(true);

  function handleNav(id: string, page?: PageId) {
    setActiveItem(id);
    if (page) onPageChange(page);
  }

  return (
    <aside className="seto-left-sidebar" aria-label="SETO Navigation">
      {/* Brand Header */}
      <div className="seto-brand-header" onClick={onNewChat} title="SETO AI Studio">
        <div className="seto-logo-symbol">
          <span className="seto-star-glyph">✦</span>
        </div>
        <span className="seto-brand-name">SETO</span>
      </div>

      {/* Main Navigation List */}
      <nav className="seto-nav-list" aria-label="Main Menu">
        <button
          type="button"
          className={`seto-nav-item ${activeItem === "home" ? "active" : ""}`}
          onClick={() => handleNav("home", "chat")}
        >
          <span className="nav-icon">🏠</span>
          <span className="nav-label">Home</span>
        </button>

        <button
          type="button"
          className={`seto-nav-item ${activeItem === "studio" ? "active" : ""}`}
          onClick={() => handleNav("studio", "widgets")}
        >
          <span className="nav-icon">✨</span>
          <span className="nav-label">Studio</span>
        </button>

        <button
          type="button"
          className={`seto-nav-item ${activeItem === "community" ? "active" : ""}`}
          onClick={() => handleNav("community")}
        >
          <span className="nav-icon">👥</span>
          <span className="nav-label">Community</span>
        </button>

        <button
          type="button"
          className={`seto-nav-item ${activeItem === "collections" ? "active" : ""}`}
          onClick={() => handleNav("collections", "memory")}
        >
          <span className="nav-icon">📁</span>
          <span className="nav-label">Collections</span>
        </button>

        <button
          type="button"
          className={`seto-nav-item ${activeItem === "library" ? "active" : ""}`}
          onClick={() => handleNav("library", "activity")}
        >
          <span className="nav-icon">⊞</span>
          <span className="nav-label">Library</span>
        </button>

        <button
          type="button"
          className={`seto-nav-item ${activeItem === "notifications" ? "active" : ""}`}
          onClick={() => handleNav("notifications")}
        >
          <span className="nav-icon">🔔</span>
          <span className="nav-label">Notifications</span>
          <span className="seto-nav-badge">8</span>
        </button>

        <button
          type="button"
          className={`seto-nav-item ${activeItem === "settings" ? "active" : ""}`}
          onClick={() => handleNav("settings", "settings")}
        >
          <span className="nav-icon">⚙️</span>
          <span className="nav-label">Settings</span>
        </button>
      </nav>

      {/* AI Tools Collapsible Section */}
      <div className="seto-ai-tools-section">
        <div
          className="seto-section-header"
          onClick={() => setAiToolsOpen(!aiToolsOpen)}
        >
          <span className="section-title">AI tools</span>
          <span className={`section-caret ${aiToolsOpen ? "open" : ""}`}>^</span>
        </div>

        {aiToolsOpen && (
          <div className="seto-subnav-list">
            <button
              type="button"
              className={`seto-subnav-item ${activeItem === "style-builder" ? "active" : ""}`}
              onClick={() => handleNav("style-builder")}
            >
              <span className="subnav-icon">🎨</span>
              <span>Style builder</span>
            </button>
            <button
              type="button"
              className={`seto-subnav-item ${activeItem === "prompt-assist" ? "active" : ""}`}
              onClick={() => handleNav("prompt-assist")}
            >
              <span className="subnav-icon">💬</span>
              <span>Prompt assist</span>
            </button>
          </div>
        )}
      </div>

      {/* Bottom User Profile & Upgrade Card (Matching Reference Image) */}
      <div className="seto-user-profile-card">
        <div className="user-profile-row">
          <div className="user-avatar-circle">
            <span>👩‍🦰</span>
          </div>
          <div className="user-text-meta">
            <strong className="user-display-name">Allison Lipshutz</strong>
            <span className="user-handle">@allison_4_li</span>
          </div>
        </div>
        <button
          type="button"
          className="seto-upgrade-btn"
          onClick={onNewChat}
          title="Upgrade to Pro Engine"
        >
          <span className="upgrade-star">✦</span>
          <span>Upgrade Now</span>
        </button>
      </div>
    </aside>
  );
}

