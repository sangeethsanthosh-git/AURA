import React, { useState } from 'react';
import {
  Moon,
  Sun,
  ShieldCheck,
  CheckCircle2,
  Trash2,
} from 'lucide-react';
import type { VoiceProfile } from '../hooks/useAuraSocket';

interface SettingsViewProps {
  activeModel: string;
  onSelectModel: (model: string) => void;
  activeVoice: string;
  onSelectVoice: (voice: string) => void;
  availableVoices: VoiceProfile[];
  isConnected: boolean;
  wakeWordActive: boolean;
  onToggleWakeWord: (enabled: boolean) => void;
  deepSearchActive: boolean;
  onToggleDeepSearch: (enabled: boolean) => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onClearAllData: () => void;
}

const AVAILABLE_MODELS = [
  {
    id: 'llama3.2:3b',
    name: 'Llama 3.2 (3B)',
    description: 'Active conversational local model — fast, nuanced, balanced (Default).',
    badge: 'Recommended',
  },
  {
    id: 'qwen3:1.7b',
    name: 'Qwen 3 (1.7B)',
    description: 'Ultra-lightweight local model with minimal RAM footprint and sub-second token latency.',
    badge: 'Fastest',
  },
  {
    id: 'deepseek-r1:1.5b',
    name: 'DeepSeek R1 (1.5B)',
    description: 'Reasoning and step-by-step thinking model with chain-of-thought capability.',
    badge: 'Reasoning',
  },
];

export const SettingsView: React.FC<SettingsViewProps> = ({
  activeModel,
  onSelectModel,
  activeVoice,
  onSelectVoice,
  availableVoices,
  isConnected,
  wakeWordActive,
  onToggleWakeWord,
  deepSearchActive,
  onToggleDeepSearch,
  theme,
  onToggleTheme,
  onClearAllData,
}) => {
  const [activeTab, setActiveTab] = useState<'general' | 'models' | 'voices' | 'privacy'>('general');

  return (
    <div className="flex-1 w-full max-w-3xl mx-auto flex flex-col h-full py-6 px-4 animate-in fade-in duration-200 select-none">
      {/* Header */}
      <div className="border-b border-[var(--border)] pb-4 mb-4">
        <h2 className="text-xl font-semibold text-[var(--text-primary)]">Preferences & Settings</h2>
        <p className="text-xs text-[var(--text-secondary)] mt-0.5">
          Configure appearance, local Ollama models, neural voice personas, and privacy
        </p>

        {/* Tab Pills */}
        <div className="flex items-center gap-1 mt-4 p-1 rounded-xl bg-[var(--surface-primary)] border border-[var(--border)] text-xs font-medium w-fit">
          <button
            type="button"
            onClick={() => setActiveTab('general')}
            className={`px-3 py-1 rounded-lg transition cursor-pointer ${
              activeTab === 'general'
                ? 'bg-[var(--surface-secondary)] text-[var(--text-primary)] font-semibold shadow-2xs'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            General & Audio
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('models')}
            className={`px-3 py-1 rounded-lg transition cursor-pointer ${
              activeTab === 'models'
                ? 'bg-[var(--surface-secondary)] text-[var(--text-primary)] font-semibold shadow-2xs'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            AI Models ({AVAILABLE_MODELS.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('voices')}
            className={`px-3 py-1 rounded-lg transition cursor-pointer ${
              activeTab === 'voices'
                ? 'bg-[var(--surface-secondary)] text-[var(--text-primary)] font-semibold shadow-2xs'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Voice Personas ({availableVoices.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('privacy')}
            className={`px-3 py-1 rounded-lg transition cursor-pointer ${
              activeTab === 'privacy'
                ? 'bg-[var(--surface-secondary)] text-[var(--text-primary)] font-semibold shadow-2xs'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Privacy & Storage
          </button>
        </div>
      </div>

      {/* Tab 1: General & Audio Settings */}
      {activeTab === 'general' && (
        <div className="flex-1 overflow-y-auto aura-scroller flex flex-col gap-4">
          {/* Appearance / Theme */}
          <div className="p-4 rounded-2xl bg-[var(--surface-primary)] border border-[var(--border)] flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-[var(--text-primary)]">Theme & Appearance</div>
              <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                Toggle between warm neutral light mode and charcoal dark mode
              </div>
            </div>
            <button
              type="button"
              onClick={onToggleTheme}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--surface-secondary)] border border-[var(--border)] text-xs font-medium text-[var(--text-primary)] hover:border-[var(--accent)] transition cursor-pointer"
            >
              {theme === 'dark' ? <Moon size={13} className="text-[var(--accent)]" /> : <Sun size={13} className="text-[var(--accent)]" />}
              <span>{theme === 'dark' ? 'Dark Charcoal' : 'Warm Neutral'}</span>
            </button>
          </div>

          {/* Wake Word Detection */}
          <div className="p-4 rounded-2xl bg-[var(--surface-primary)] border border-[var(--border)] flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-[var(--text-primary)]">Wake Word Detection ("Hey Aura")</div>
              <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                Listen continuously in the background for the wake phrase to trigger listening
              </div>
            </div>
            <button
              type="button"
              onClick={() => onToggleWakeWord(!wakeWordActive)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold border transition cursor-pointer ${
                wakeWordActive
                  ? 'bg-amber-50 text-amber-800 border-amber-300'
                  : 'bg-[var(--surface-secondary)] text-[var(--text-secondary)] border-[var(--border)]'
              }`}
            >
              {wakeWordActive ? 'Active' : 'Disabled'}
            </button>
          </div>

          {/* Wikipedia Deep Search */}
          <div className="p-4 rounded-2xl bg-[var(--surface-primary)] border border-[var(--border)] flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-[var(--text-primary)]">Wikipedia Deep Search Integration</div>
              <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                Automatically verify factual queries against encyclopedia articles with real thumbnails
              </div>
            </div>
            <button
              type="button"
              onClick={() => onToggleDeepSearch(!deepSearchActive)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold border transition cursor-pointer ${
                deepSearchActive
                  ? 'bg-blue-50 text-blue-800 border-blue-300'
                  : 'bg-[var(--surface-secondary)] text-[var(--text-secondary)] border-[var(--border)]'
              }`}
            >
              {deepSearchActive ? 'Enabled' : 'Disabled'}
            </button>
          </div>

          {/* Connection Status */}
          <div className="p-4 rounded-2xl bg-[var(--surface-primary)] border border-[var(--border)] flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-[var(--text-primary)]">Local API & Ollama Status</div>
              <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                FastAPI WebSocket on port 8000 and Ollama daemon on port 11434
              </div>
            </div>
            <span
              className={`px-3 py-1 rounded-full text-xs font-semibold ${
                isConnected
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-rose-50 text-rose-700 border border-rose-200'
              }`}
            >
              {isConnected ? 'Online & Ready' : 'Disconnected'}
            </span>
          </div>
        </div>
      )}

      {/* Tab 2: AI Models */}
      {activeTab === 'models' && (
        <div className="flex-1 overflow-y-auto aura-scroller flex flex-col gap-2.5">
          {AVAILABLE_MODELS.map((model) => {
            const isSelected = activeModel === model.id;
            return (
              <div
                key={model.id}
                onClick={() => onSelectModel(model.id)}
                className={`p-4 rounded-2xl border transition cursor-pointer flex items-center justify-between ${
                  isSelected
                    ? 'bg-[var(--surface-primary)] border-[var(--accent)] shadow-xs'
                    : 'bg-[var(--surface-primary)]/80 hover:bg-[var(--surface-primary)] border-[var(--border)]'
                }`}
              >
                <div className="flex flex-col gap-1 min-w-0 pr-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[var(--text-primary)]">{model.name}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-[var(--surface-secondary)] text-[var(--text-secondary)]">
                      {model.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                    {model.description}
                  </p>
                </div>
                {isSelected && <CheckCircle2 size={18} className="text-[var(--accent)] shrink-0" />}
              </div>
            );
          })}
        </div>
      )}

      {/* Tab 3: Voice Personas */}
      {activeTab === 'voices' && (
        <div className="flex-1 overflow-y-auto aura-scroller flex flex-col gap-2">
          {availableVoices.map((v) => {
            const isSelected = activeVoice.toLowerCase() === v.name.toLowerCase();
            return (
              <div
                key={v.id}
                onClick={() => onSelectVoice(v.name)}
                className={`p-3.5 rounded-2xl border transition cursor-pointer flex items-center justify-between ${
                  isSelected
                    ? 'bg-[var(--surface-primary)] border-[var(--accent)] shadow-xs'
                    : 'bg-[var(--surface-primary)]/80 hover:bg-[var(--surface-primary)] border-[var(--border)]'
                }`}
              >
                <div className="flex flex-col gap-0.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[var(--text-primary)]">{v.name}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-[var(--surface-secondary)] text-[var(--text-secondary)]">
                      {v.gender}
                    </span>
                    {v.badge && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-[var(--accent-light)] text-[var(--accent)]">
                        {v.badge}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">{v.description}</p>
                </div>
                {isSelected && <CheckCircle2 size={18} className="text-[var(--accent)] shrink-0 ml-2" />}
              </div>
            );
          })}
        </div>
      )}

      {/* Tab 4: Privacy & Storage */}
      {activeTab === 'privacy' && (
        <div className="flex-1 overflow-y-auto aura-scroller flex flex-col gap-4">
          <div className="p-4 rounded-2xl bg-[var(--surface-primary)] border border-[var(--border)] flex items-start gap-3">
            <ShieldCheck size={20} className="text-emerald-600 mt-0.5 shrink-0" />
            <div>
              <div className="text-xs font-semibold text-[var(--text-primary)]">100% Local-First & Private</div>
              <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed mt-1">
                Your conversations, notes, audio recordings, and tasks stay on your local device. Ollama models run completely offline on your hardware, and Faster-Whisper transcribes speech locally using CPU INT8 inference.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-[var(--surface-primary)] border border-[var(--border)] flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-[var(--text-primary)]">Clear Stored Session Data</div>
              <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                Reset local session cache and notes memory
              </div>
            </div>
            <button
              type="button"
              onClick={onClearAllData}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold border border-rose-200 transition cursor-pointer"
            >
              <Trash2 size={13} />
              <span>Reset Data</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
