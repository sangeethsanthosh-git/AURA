import React, { useState } from 'react';
import {
  Plus,
  Search,
  MessageSquare,
  Mic,
  FileText,
  CheckSquare,
  Sliders,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Trash2,
  Edit2,
  Volume2,
} from 'lucide-react';

export type ScreenType = 'home' | 'chat' | 'voice' | 'notes' | 'tasks' | 'settings';

export interface RecentChat {
  id: string;
  title: string;
  timestamp: string;
  prompt: string;
}

interface SidebarProps {
  currentScreen: ScreenType;
  onNavigate: (screen: ScreenType) => void;
  onNewChat: () => void;
  recentChats: RecentChat[];
  onSelectRecentChat: (chat: RecentChat) => void;
  onDeleteRecentChat: (id: string, e: React.MouseEvent) => void;
  onRenameRecentChat: (id: string, newTitle: string) => void;
  activeModel: string;
  activeVoice: string;
  isConnected: boolean;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentScreen,
  onNavigate,
  onNewChat,
  recentChats,
  onSelectRecentChat,
  onDeleteRecentChat,
  onRenameRecentChat,
  activeModel,
  activeVoice,
  isConnected,
  isCollapsed,
  onToggleCollapse,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const filteredRecents = recentChats.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleStartRename = (chat: RecentChat, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(chat.id);
    setEditTitle(chat.title);
  };

  const handleSaveRename = (id: string, e: React.KeyboardEvent | React.FocusEvent) => {
    if ('key' in e && e.key !== 'Enter') return;
    if (editTitle.trim()) {
      onRenameRecentChat(id, editTitle.trim());
    }
    setEditingId(null);
  };

  if (isCollapsed) {
    return (
      <aside className="w-16 h-full aura-sidebar flex flex-col items-center py-4 justify-between select-none shrink-0 z-20">
        <div className="flex flex-col items-center gap-3">
          {/* macOS window dots */}
          <div className="flex items-center gap-1.5 mb-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FF5F56]" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#FFBD2E]" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#27C93F]" />
          </div>

          <button
            type="button"
            onClick={onNewChat}
            title="New Chat (+)"
            className="w-10 h-10 rounded-xl bg-[var(--surface-primary)] hover:bg-[var(--surface-secondary)] border border-[var(--border)] text-[var(--text-primary)] flex items-center justify-center transition shadow-2xs cursor-pointer"
          >
            <Plus size={18} />
          </button>

          <button
            type="button"
            onClick={() => onNavigate('home')}
            title="Home"
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition cursor-pointer ${
              currentScreen === 'home'
                ? 'bg-[var(--surface-secondary)] text-[var(--accent)] font-semibold'
                : 'hover:bg-[var(--surface-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <MessageSquare size={17} />
          </button>

          <button
            type="button"
            onClick={() => onNavigate('voice')}
            title="Voice Studio"
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition cursor-pointer ${
              currentScreen === 'voice'
                ? 'bg-[var(--surface-secondary)] text-[var(--accent)] font-semibold'
                : 'hover:bg-[var(--surface-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <Mic size={17} />
          </button>

          <button
            type="button"
            onClick={() => onNavigate('notes')}
            title="Notes"
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition cursor-pointer ${
              currentScreen === 'notes'
                ? 'bg-[var(--surface-secondary)] text-[var(--accent)] font-semibold'
                : 'hover:bg-[var(--surface-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <FileText size={17} />
          </button>

          <button
            type="button"
            onClick={() => onNavigate('tasks')}
            title="Tasks & Reminders"
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition cursor-pointer ${
              currentScreen === 'tasks'
                ? 'bg-[var(--surface-secondary)] text-[var(--accent)] font-semibold'
                : 'hover:bg-[var(--surface-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <CheckSquare size={17} />
          </button>
        </div>

        <div className="flex flex-col items-center gap-3">
          <button
            type="button"
            onClick={() => onNavigate('settings')}
            title="Settings"
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition cursor-pointer ${
              currentScreen === 'settings'
                ? 'bg-[var(--surface-secondary)] text-[var(--accent)] font-semibold'
                : 'hover:bg-[var(--surface-primary)] text-[var(--text-secondary)]'
            }`}
          >
            <Sliders size={17} />
          </button>

          <button
            type="button"
            onClick={onToggleCollapse}
            title="Expand Sidebar"
            className="w-8 h-8 rounded-lg hover:bg-[var(--surface-primary)] text-[var(--text-secondary)] flex items-center justify-center transition cursor-pointer"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-[245px] h-full aura-sidebar flex flex-col justify-between py-4 select-none shrink-0 z-20">
      <div className="flex flex-col h-full overflow-hidden">
        {/* Top Window Header */}
        <div className="px-5 pb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#FF5F56] border border-[#E0443E]/40" />
            <span className="w-3 h-3 rounded-full bg-[#FFBD2E] border border-[#DEA123]/40" />
            <span className="w-3 h-3 rounded-full bg-[#27C93F] border border-[#1AAB29]/40" />
          </div>

          <button
            type="button"
            onClick={onToggleCollapse}
            title="Collapse Sidebar"
            className="p-1 rounded-md text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-black/[0.04] transition cursor-pointer"
          >
            <ChevronLeft size={16} />
          </button>
        </div>

        {/* Primary Action Buttons */}
        <div className="px-3 pb-2 flex flex-col gap-1 border-b border-[var(--border)]">
          <button
            type="button"
            onClick={onNewChat}
            className="w-full flex items-center gap-2 px-3 py-1.5 rounded-xl text-[13px] font-medium text-[var(--text-primary)] hover:bg-[var(--surface-primary)] transition cursor-pointer text-left"
          >
            <Plus size={15} className="text-[var(--text-secondary)]" />
            <span>New chat</span>
          </button>

          <button
            type="button"
            onClick={() => setIsSearchOpen((prev) => !prev)}
            className="w-full flex items-center gap-2 px-3 py-1.5 rounded-xl text-[13px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-primary)] transition cursor-pointer text-left"
          >
            <Search size={15} />
            <span>Search</span>
          </button>

          {isSearchOpen && (
            <div className="px-2 py-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter recents..."
                autoFocus
                className="w-full bg-[var(--surface-primary)] px-2.5 py-1 text-xs rounded-lg border border-[var(--border)] focus:outline-none text-[var(--text-primary)] placeholder-[var(--text-tertiary)]"
              />
            </div>
          )}
        </div>

        {/* Navigation Modules */}
        <div className="px-3 py-2 flex flex-col gap-0.5 border-b border-[var(--border)]">
          <button
            type="button"
            onClick={() => onNavigate('home')}
            className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-xl text-[13px] font-medium transition text-left cursor-pointer ${
              currentScreen === 'home' || currentScreen === 'chat'
                ? 'bg-[var(--surface-secondary)] text-[var(--text-primary)] font-semibold'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-primary)]'
            }`}
          >
            <MessageSquare size={15} />
            <span>Chats</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('voice')}
            className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-xl text-[13px] font-medium transition text-left cursor-pointer ${
              currentScreen === 'voice'
                ? 'bg-[var(--surface-secondary)] text-[var(--text-primary)] font-semibold'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-primary)]'
            }`}
          >
            <Mic size={15} />
            <span>Voice Studio</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('notes')}
            className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-xl text-[13px] font-medium transition text-left cursor-pointer ${
              currentScreen === 'notes'
                ? 'bg-[var(--surface-secondary)] text-[var(--text-primary)] font-semibold'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-primary)]'
            }`}
          >
            <FileText size={15} />
            <span>Notes</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('tasks')}
            className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-xl text-[13px] font-medium transition text-left cursor-pointer ${
              currentScreen === 'tasks'
                ? 'bg-[var(--surface-secondary)] text-[var(--text-primary)] font-semibold'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-primary)]'
            }`}
          >
            <CheckSquare size={15} />
            <span>Tasks</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('settings')}
            className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-xl text-[13px] font-medium transition text-left cursor-pointer ${
              currentScreen === 'settings'
                ? 'bg-[var(--surface-secondary)] text-[var(--text-primary)] font-semibold'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-primary)]'
            }`}
          >
            <Sliders size={15} />
            <span>Settings</span>
          </button>
        </div>

        {/* RECENTS Section */}
        <div className="flex-1 overflow-y-auto px-3 py-2.5 aura-scroller">
          <div className="px-2 pb-1.5 text-[10px] font-semibold tracking-wider text-[var(--text-tertiary)] uppercase flex items-center justify-between">
            <span>Recent Conversations</span>
            <span className="font-mono text-[9px]">{filteredRecents.length}</span>
          </div>

          <div className="flex flex-col gap-0.5">
            {filteredRecents.map((chat) => (
              <div
                key={chat.id}
                onClick={() => onSelectRecentChat(chat)}
                className="group relative w-full text-left px-2.5 py-1.5 rounded-xl hover:bg-[var(--surface-primary)] transition cursor-pointer flex items-center justify-between"
              >
                <div className="min-w-0 flex-1">
                  {editingId === chat.id ? (
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => handleSaveRename(chat.id, e)}
                      onBlur={(e) => handleSaveRename(chat.id, e)}
                      autoFocus
                      onClick={(e) => e.stopPropagation()}
                      className="w-full text-xs bg-[var(--surface-primary)] px-1.5 py-0.5 border border-[var(--accent)] rounded focus:outline-none"
                    />
                  ) : (
                    <>
                      <div className="text-[12px] font-medium text-[var(--text-primary)] truncate group-hover:text-[var(--accent)] transition">
                        {chat.title}
                      </div>
                      <div className="text-[10px] text-[var(--text-tertiary)] truncate">
                        {chat.timestamp}
                      </div>
                    </>
                  )}
                </div>

                {/* Actions on hover: Rename & Delete */}
                <div className="hidden group-hover:flex items-center gap-1 pl-1 shrink-0">
                  <button
                    type="button"
                    onClick={(e) => handleStartRename(chat, e)}
                    title="Rename"
                    className="p-1 rounded text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-black/[0.04]"
                  >
                    <Edit2 size={11} />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => onDeleteRecentChat(chat.id, e)}
                    title="Delete"
                    className="p-1 rounded text-[var(--text-tertiary)] hover:text-rose-600 hover:bg-rose-50"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* User Status Footer */}
      <div className="px-3 pt-3 border-t border-[var(--border)]">
        <div
          onClick={() => onNavigate('settings')}
          className="w-full flex items-center justify-between p-2 rounded-2xl hover:bg-[var(--surface-primary)] transition cursor-pointer"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full bg-[var(--text-primary)] text-[var(--surface-primary)] flex items-center justify-center font-semibold text-xs shrink-0">
              L
            </div>
            <div className="min-w-0 flex flex-col">
              <span className="text-xs font-semibold text-[var(--text-primary)] truncate">Lukas</span>
              <span className="text-[10px] text-[var(--text-secondary)] truncate flex items-center gap-1">
                <Volume2 size={9} className="text-[var(--accent)]" />
                {activeVoice} · {activeModel}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <span
              title={isConnected ? 'Ollama & API Connected' : 'Disconnected'}
              className={`w-2 h-2 rounded-full ${isConnected ? 'bg-[var(--status-success)]' : 'bg-[var(--status-error)] animate-pulse'}`}
            />
            <ChevronDown size={14} className="text-[var(--text-tertiary)]" />
          </div>
        </div>
      </div>
    </aside>
  );
};
