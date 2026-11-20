import React, { useState } from 'react';
import {
  Layers,
  ListTodo,
  FileText,
  BookOpen,
  X,
  ExternalLink,
  Sparkles,
  Cpu,
  Volume2,
} from 'lucide-react';
import type { ChatMessage } from '../hooks/useAuraSocket';

interface ContextInspectorProps {
  messages: ChatMessage[];
  activeModel: string;
  activeVoice: string;
  onClose: () => void;
}

export const ContextInspector: React.FC<ContextInspectorProps> = ({
  messages,
  activeModel,
  activeVoice,
  onClose,
}) => {
  const [tab, setTab] = useState<'context' | 'plan' | 'notes' | 'sources'>('context');
  const [scratchpadNote, setScratchpadNote] = useState(() => {
    try {
      return localStorage.getItem('aura_inspector_notes') || '';
    } catch {
      return '';
    }
  });

  const handleSaveScratchpad = (val: string) => {
    setScratchpadNote(val);
    try {
      localStorage.setItem('aura_inspector_notes', val);
    } catch {}
  };

  // Collect all Wikipedia sources from messages
  const allArticles = messages.flatMap((m) => m.wiki?.articles || []);
  const uniqueArticles = Array.from(
    new Map(allArticles.map((a) => [a.url, a])).values()
  );

  const userCount = messages.filter((m) => m.role === 'user').length;
  const assistantCount = messages.filter((m) => m.role === 'assistant').length;

  return (
    <aside className="w-[300px] h-full bg-[var(--bg-sidebar)] border-l border-[var(--border)] flex flex-col justify-between p-3.5 shrink-0 select-none z-10 animate-in slide-in-from-right duration-150">
      <div className="flex flex-col h-full overflow-hidden">
        {/* Header & Close Button */}
        <div className="flex items-center justify-between pb-2.5 border-b border-[var(--border)]">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-[var(--text-primary)]">
            <Sparkles size={13} className="text-[var(--accent)]" />
            <span>Context Inspector</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-black/[0.04] transition cursor-pointer"
          >
            <X size={15} />
          </button>
        </div>

        {/* 4 Tabs: Context | Plan | Notes | Sources */}
        <div className="flex items-center gap-1 p-1 bg-[var(--surface-secondary)] rounded-xl my-3 text-[11px] font-medium">
          <button
            type="button"
            onClick={() => setTab('context')}
            className={`flex-1 py-1 rounded-lg flex items-center justify-center gap-1 transition cursor-pointer ${
              tab === 'context'
                ? 'bg-[var(--surface-primary)] text-[var(--text-primary)] shadow-2xs font-semibold'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <Layers size={11} />
            <span>Context</span>
          </button>
          <button
            type="button"
            onClick={() => setTab('plan')}
            className={`flex-1 py-1 rounded-lg flex items-center justify-center gap-1 transition cursor-pointer ${
              tab === 'plan'
                ? 'bg-[var(--surface-primary)] text-[var(--text-primary)] shadow-2xs font-semibold'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <ListTodo size={11} />
            <span>Plan</span>
          </button>
          <button
            type="button"
            onClick={() => setTab('notes')}
            className={`flex-1 py-1 rounded-lg flex items-center justify-center gap-1 transition cursor-pointer ${
              tab === 'notes'
                ? 'bg-[var(--surface-primary)] text-[var(--text-primary)] shadow-2xs font-semibold'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <FileText size={11} />
            <span>Notes</span>
          </button>
          <button
            type="button"
            onClick={() => setTab('sources')}
            className={`flex-1 py-1 rounded-lg flex items-center justify-center gap-1 transition cursor-pointer ${
              tab === 'sources'
                ? 'bg-[var(--surface-primary)] text-[var(--text-primary)] shadow-2xs font-semibold'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <BookOpen size={11} />
            <span>Sources</span>
          </button>
        </div>

        {/* Tab Contents */}
        <div className="flex-1 overflow-y-auto aura-scroller pr-1 flex flex-col gap-3 text-xs">
          {tab === 'context' && (
            <div className="flex flex-col gap-3">
              <div className="p-3 bg-[var(--surface-primary)] rounded-xl border border-[var(--border)] flex flex-col gap-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                  Session Statistics
                </span>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[var(--text-secondary)]">Total Turns</span>
                  <span className="font-semibold text-[var(--text-primary)]">{messages.length}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[var(--text-secondary)]">User Queries</span>
                  <span className="font-medium text-[var(--text-primary)]">{userCount}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[var(--text-secondary)]">Assistant Responses</span>
                  <span className="font-medium text-[var(--text-primary)]">{assistantCount}</span>
                </div>
              </div>

              <div className="p-3 bg-[var(--surface-primary)] rounded-xl border border-[var(--border)] flex flex-col gap-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                  Hardware Engine
                </span>
                <div className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1 text-[var(--text-secondary)]">
                    <Cpu size={11} className="text-[var(--accent)]" /> Model
                  </span>
                  <span className="font-mono text-[11px] font-semibold text-[var(--text-primary)]">
                    {activeModel}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1 text-[var(--text-secondary)]">
                    <Volume2 size={11} className="text-[var(--accent)]" /> TTS Persona
                  </span>
                  <span className="font-medium text-[11px] text-[var(--text-primary)]">
                    {activeVoice}
                  </span>
                </div>
              </div>
            </div>
          )}

          {tab === 'plan' && (
            <div className="flex flex-col gap-2.5">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                Active Execution Workflow
              </span>
              <div className="p-3 bg-[var(--surface-primary)] rounded-xl border border-[var(--border)] flex flex-col gap-2 leading-relaxed text-[#78716C]">
                <div className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-[var(--surface-secondary)] text-[var(--accent)] text-[10px] font-bold flex items-center justify-center shrink-0">1</span>
                  <span>Acoustic Pre-roll & VAD Recording (Faster-Whisper CPU INT8)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-[var(--surface-secondary)] text-[var(--accent)] text-[10px] font-bold flex items-center justify-center shrink-0">2</span>
                  <span>Wikipedia Fact Extraction & Context Isolation</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-[var(--surface-secondary)] text-[var(--accent)] text-[10px] font-bold flex items-center justify-center shrink-0">3</span>
                  <span>Local LLM Phrasal Streaming & Edge-TTS Audio Generation</span>
                </div>
              </div>
            </div>
          )}

          {tab === 'notes' && (
            <div className="flex flex-col gap-2 h-full">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                Session Scratchpad
              </span>
              <textarea
                value={scratchpadNote}
                onChange={(e) => handleSaveScratchpad(e.target.value)}
                placeholder="Take quick notes during your conversation..."
                className="w-full flex-1 min-h-[220px] bg-[var(--surface-primary)] p-3 rounded-xl border border-[var(--border)] text-xs text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none resize-none aura-scroller select-text font-mono"
              />
            </div>
          )}

          {tab === 'sources' && (
            <div className="flex flex-col gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                Referenced Knowledge ({uniqueArticles.length})
              </span>
              {uniqueArticles.length === 0 ? (
                <div className="p-4 text-center text-[var(--text-tertiary)] italic text-xs bg-[var(--surface-primary)] rounded-xl border border-[var(--border)]">
                  No Wikipedia knowledge sources cited in this session yet.
                </div>
              ) : (
                uniqueArticles.map((art) => (
                  <a
                    key={art.url}
                    href={art.url}
                    target="_blank"
                    rel="noreferrer"
                    className="p-2.5 rounded-xl bg-[var(--surface-primary)] hover:bg-[var(--surface-secondary)] border border-[var(--border)] flex items-center justify-between text-xs text-[var(--text-primary)] transition"
                  >
                    <span className="truncate max-w-[210px]">{art.title}</span>
                    <ExternalLink size={11} className="text-[var(--text-tertiary)]" />
                  </a>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
