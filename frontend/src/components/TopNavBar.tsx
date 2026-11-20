import React from 'react';
import {
  Sliders,
  PanelRight,
  Sparkles,
  MessageSquare,
  Mic,
  FileText,
  CheckSquare,
} from 'lucide-react';
import type { ScreenType } from './Sidebar';

interface TopNavBarProps {
  currentScreen: ScreenType;
  onNavigate: (screen: ScreenType) => void;
  isConnected: boolean;
  onOpenSettings: () => void;
  isInspectorOpen: boolean;
  onToggleInspector: () => void;
  activeModel: string;
}

export const TopNavBar: React.FC<TopNavBarProps> = ({
  currentScreen,
  onNavigate,
  isConnected,
  onOpenSettings,
  isInspectorOpen,
  onToggleInspector,
  activeModel,
}) => {
  return (
    <header className="w-full h-12 flex items-center justify-between px-6 select-none shrink-0 z-10 border-b border-[var(--border)] bg-[var(--surface-primary)]/50 backdrop-blur-md">
      {/* Left Model & App Title */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold tracking-tight text-[var(--text-primary)]">
          AURA
        </span>
        <span className="text-[10px] font-mono text-[var(--text-tertiary)] hidden sm:inline">
          / {activeModel}
        </span>
      </div>

      {/* Top Center Segmented Pill Switcher (Reference Image 1: [ Chats | Colab | Code ]) */}
      <div className="flex items-center p-1 bg-[var(--surface-secondary)] rounded-full border border-[var(--border)] shadow-2xs">
        <button
          type="button"
          onClick={() => onNavigate(currentScreen === 'chat' ? 'chat' : 'home')}
          className={`flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-medium transition cursor-pointer ${
            currentScreen === 'home' || currentScreen === 'chat'
              ? 'bg-[var(--surface-primary)] text-[var(--text-primary)] shadow-xs font-semibold'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <MessageSquare size={12} />
          <span>Chats</span>
        </button>

        <button
          type="button"
          onClick={() => onNavigate('voice')}
          className={`flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-medium transition cursor-pointer ${
            currentScreen === 'voice'
              ? 'bg-[var(--surface-primary)] text-[var(--text-primary)] shadow-xs font-semibold'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <Mic size={12} />
          <span>Voice</span>
        </button>

        <button
          type="button"
          onClick={() => onNavigate('notes')}
          className={`flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-medium transition cursor-pointer ${
            currentScreen === 'notes'
              ? 'bg-[var(--surface-primary)] text-[var(--text-primary)] shadow-xs font-semibold'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <FileText size={12} />
          <span>Notes</span>
        </button>

        <button
          type="button"
          onClick={() => onNavigate('tasks')}
          className={`flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-medium transition cursor-pointer ${
            currentScreen === 'tasks'
              ? 'bg-[var(--surface-primary)] text-[var(--text-primary)] shadow-xs font-semibold'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <CheckSquare size={12} />
          <span>Tasks</span>
        </button>
      </div>

      {/* Right Controls: Pro Engine Badge, Context Inspector Toggle, Settings & Status */}
      <div className="flex items-center gap-2">
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[var(--surface-secondary)] border border-[var(--border)] text-[11px] text-[var(--text-secondary)]">
          <Sparkles size={11} className="text-[var(--accent)]" />
          <span className="font-medium text-[var(--text-primary)]">Local Neural</span>
        </div>

        {/* Right Inspector Toggle */}
        <button
          type="button"
          onClick={onToggleInspector}
          title={isInspectorOpen ? 'Hide Context Inspector' : 'Show Context Inspector'}
          className={`p-1.5 rounded-lg border transition cursor-pointer ${
            isInspectorOpen
              ? 'bg-[var(--surface-secondary)] border-[var(--accent)] text-[var(--accent)]'
              : 'bg-[var(--surface-primary)] border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <PanelRight size={15} />
        </button>

        {/* Settings button */}
        <button
          type="button"
          onClick={onOpenSettings}
          title="Settings"
          className="p-1.5 rounded-lg bg-[var(--surface-primary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer"
        >
          <Sliders size={15} />
        </button>

        {/* Connection status indicator */}
        <div
          title={isConnected ? 'Backend Connected' : 'Backend Offline'}
          className={`w-2.5 h-2.5 rounded-full ml-1 ${
            isConnected
              ? 'bg-[var(--status-success)] shadow-xs shadow-emerald-500/50'
              : 'bg-[var(--status-error)] animate-pulse'
          }`}
        />
      </div>
    </header>
  );
};
