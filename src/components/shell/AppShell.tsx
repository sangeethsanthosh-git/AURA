import { ReactNode, useEffect, useState } from "react";
import { useAuraRuntime } from "../../state/AuraContext";
import { readAppSettings, subscribeToAppSettings } from "../../state/appSettings";
import {
  DiamondLogo,
} from "../ui/Icons";
import { AuraCompanionWidget } from "../widgets/AuraCompanionWidget";

export type PageId =
  | "chat"
  | "dashboard"
  | "schedule"
  | "news"
  | "widgets"
  | "memory"
  | "activity"
  | "voice"
  | "settings";

interface AppShellProps {
  activePage: PageId;
  onPageChange: (page: PageId) => void;
  onNewSession?: () => void;
  companionVisible?: boolean;
  onToggleCompanion?: () => void;
  children: ReactNode;
}

export function AppShell({
  activePage,
  onPageChange,
  companionVisible = false,
  onToggleCompanion,
  children,
}: AppShellProps) {
  const { backend, voiceState } = useAuraRuntime();
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [profileName, setProfileName] = useState(() => readAppSettings().profileName);
  const [assistantName, setAssistantName] = useState(() => readAppSettings().assistantName);
  const [avatarImage, setAvatarImage] = useState(() => readAppSettings().avatarImage);
  const [backgroundImage, setBackgroundImage] = useState(() => readAppSettings().backgroundImage);
  const [themeMode, setThemeMode] = useState(() => readAppSettings().themeMode);
  const canShowAssistant = activePage !== "chat";

  useEffect(() => subscribeToAppSettings(() => {
    const next = readAppSettings();
    setProfileName(next.profileName);
    setAssistantName(next.assistantName);
    setAvatarImage(next.avatarImage);
    setBackgroundImage(next.backgroundImage);
    setThemeMode(next.themeMode);
  }), []);

  const resolvedTheme = themeMode === "system"
    ? (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    : themeMode;

  return (
    <div
      className="premium-saas-root-environment"
      aria-label="AURA Premium SaaS Suite"
      style={{
        ["--aura-app-wallpaper" as string]: backgroundImage ? `url(${backgroundImage})` : "none",
        ["--bg-gradient" as string]: resolvedTheme === "dark"
          ? "linear-gradient(135deg, #0b1220 0%, #111827 50%, #1f2937 100%)"
          : "linear-gradient(135deg, #f5f7fb 0%, #edf2ff 100%)",
        ["--window-bg" as string]: resolvedTheme === "dark" ? "rgba(9, 12, 20, 0.92)" : "rgba(255, 255, 255, 0.92)",
        ["--window-border" as string]: resolvedTheme === "dark" ? "rgba(148, 163, 184, 0.18)" : "#e2e8f0",
        ["--surface-white" as string]: resolvedTheme === "dark" ? "rgba(15, 23, 42, 0.92)" : "#ffffff",
        ["--border-light" as string]: resolvedTheme === "dark" ? "rgba(148, 163, 184, 0.18)" : "rgba(148, 163, 184, 0.22)",
        ["--text-primary" as string]: resolvedTheme === "dark" ? "#e2e8f0" : "#0f172a",
        ["--text-secondary" as string]: resolvedTheme === "dark" ? "#94a3b8" : "#475569",
        ["--text-muted" as string]: resolvedTheme === "dark" ? "#64748b" : "#94a3b8",
        ["--accent-black" as string]: resolvedTheme === "dark" ? "#e2e8f0" : "#0f172a",
        ["--music-overlay" as string]: resolvedTheme === "dark" ? "linear-gradient(180deg, rgba(15, 23, 42, 0.48) 0%, rgba(15, 23, 42, 0.88) 100%)" : "linear-gradient(180deg, rgba(255, 255, 255, 0.45) 0%, rgba(255, 255, 255, 0.82) 100%)",
        ["--music-banner-overlay" as string]: resolvedTheme === "dark" ? "linear-gradient(180deg, rgba(15, 23, 42, 0.58) 0%, rgba(15, 23, 42, 0.92) 100%)" : "linear-gradient(180deg, rgba(255, 255, 255, 0.55) 0%, rgba(255, 255, 255, 0.88) 100%)",
      }}
    >
      <div className="premium-saas-window-frame">
        {/* Top Suite Navigation & Controls Bar */}
        <header className="premium-top-navigation-bar">
          {/* Left Brand Pill */}
          <div
            className="brand-identity-box"
            onClick={() => onPageChange("chat")}
            title="AURA Home"
          >
            <div className="brand-gem-icon">
              <DiamondLogo />
            </div>
            <span className="brand-saas-name">AURA</span>
          </div>

          {/* Center Suite App Switcher */}
          <nav className="suite-app-switcher-tabs" aria-label="Suite Modules">
            <button
              type="button"
              className={`suite-tab-btn ${activePage === "chat" ? "active" : ""}`}
              onClick={() => onPageChange("chat")}
            >
              <span className="tab-icon">💬</span>
              <span>Studio & AI</span>
            </button>
            <button
              type="button"
              className={`suite-tab-btn ${activePage === "dashboard" ? "active" : ""}`}
              onClick={() => onPageChange("dashboard")}
            >
              <span className="tab-icon">📊</span>
              <span>Dashboard</span>
            </button>
            <button
              type="button"
              className={`suite-tab-btn ${activePage === "schedule" ? "active" : ""}`}
              onClick={() => onPageChange("schedule")}
            >
              <span className="tab-icon">📅</span>
              <span>Schedule</span>
            </button>
            <button
              type="button"
              className={`suite-tab-btn ${activePage === "news" ? "active" : ""}`}
              onClick={() => onPageChange("news")}
            >
              <span className="tab-icon">📰</span>
              <span>News</span>
            </button>
            <button
              type="button"
              className={`suite-tab-btn ${activePage === "widgets" ? "active" : ""}`}
              onClick={() => onPageChange("widgets")}
            >
              <span className="tab-icon">🎵</span>
              <span>Media & Tools</span>
            </button>
            <button
              type="button"
              className={`suite-tab-btn ${activePage === "memory" ? "active" : ""}`}
              onClick={() => onPageChange("memory")}
            >
              <span className="tab-icon">🧠</span>
              <span>Memory</span>
            </button>
            <button
              type="button"
              className={`suite-tab-btn ${activePage === "settings" ? "active" : ""}`}
              onClick={() => onPageChange("settings")}
            >
              <span className="tab-icon">⚙️</span>
              <span>Settings</span>
            </button>
          </nav>

          {/* Right Status & Layout Toggles */}
          <div className="top-bar-right-cluster">
            {/* Live Engine Indicator */}
            <div className="engine-badge-pill" title={`Local AI Engine: ${backend}`}>
              <span
                className="engine-live-dot"
                style={{
                  backgroundColor: backend === "READY" ? "#10b981" : "#f59e0b",
                }}
              />
              <span className="engine-text">Local ({backend})</span>
              {voiceState === "RECORDING" && <span className="voice-active-indicator">🎙️ Live</span>}
            </div>

            <button
              type="button"
              className={`engine-badge-pill companion-toggle-pill ${companionVisible ? "active" : ""}`}
              onClick={() => onToggleCompanion?.()}
              title={companionVisible ? "Hide AURA companion" : "Show AURA companion"}
              aria-label={companionVisible ? "Hide AURA companion" : "Show AURA companion"}
            >
              <span className="engine-text">{assistantName || "Companion"}</span>
            </button>

            {/* User Profile Mini Pill */}
            <div className="top-user-pill">
              {avatarImage ? <img src={avatarImage} alt="" className="user-avatar-mini user-avatar-mini--image" /> : <span className="user-avatar-mini">👤</span>}
              <span className="user-name-label">{profileName}</span>
            </div>
            <div className="app-window-controls" aria-label="Window controls">
              <button type="button" className="app-window-btn" onClick={() => void window.aura?.window.minimize()} title="Minimize" aria-label="Minimize window">
                -
              </button>
              <button type="button" className="app-window-btn" onClick={() => void window.aura?.window.maximize()} title="Maximize" aria-label="Maximize window">
                □
              </button>
              <button type="button" className="app-window-btn app-window-btn--close" onClick={() => void window.aura?.window.close()} title="Close to companion" aria-label="Close main window to companion">
                x
              </button>
            </div>
          </div>
        </header>

        {/* Main Application Body */}
        <main className="premium-saas-main-canvas">{children}</main>
        {canShowAssistant && (
          <button
            type="button"
            className={`aura-companion-fab ${assistantOpen ? "active" : ""}`}
            onClick={() => setAssistantOpen((open) => !open)}
            title={assistantOpen ? "Hide AI Assistant" : "Show AI Assistant"}
            aria-label={assistantOpen ? "Hide AI Assistant" : "Show AI Assistant"}
          >
            AI
          </button>
        )}

        {canShowAssistant && assistantOpen && (
          <aside className="aura-global-companion-dock" aria-label="Global AI Assistant">
            <AuraCompanionWidget />
          </aside>
        )}
      </div>
    </div>
  );
}
