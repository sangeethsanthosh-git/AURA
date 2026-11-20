import React, { useState, useRef, useEffect } from 'react';
import {
  Code2,
  FileSpreadsheet,
  Lightbulb,
  Globe,
  Paperclip,
  Mic,
  ArrowUp,
  ChevronDown,
  Volume2,
  Square,
  Cpu,
} from 'lucide-react';
import type { AssistantState, VoiceProfile } from '../hooks/useAuraSocket';
import { VoiceOrb } from './VoiceOrb';

interface HomeViewProps {
  onSendText: (text: string) => void;
  state: AssistantState;
  activeModel: string;
  activeVoice: string;
  availableVoices: VoiceProfile[];
  deepSearchActive: boolean;
  onStartListening: () => void;
  onStopAudio: () => void;
  onOpenSettings: () => void;
  onToggleDeepSearch: (enabled: boolean) => void;
  onSelectModel: (model: string) => void;
  onSelectVoice: (voice: string) => void;
  disabled?: boolean;
}

const QUICK_START_CARDS = [
  {
    id: 'script',
    title: 'Write a script',
    description: 'Write a TypeScript script that fetches data from an API and processes it.',
    icon: <Code2 size={17} className="text-[#D68B55]" />,
    prompt: 'Write a TypeScript script that fetches data from an API and processes it.',
  },
  {
    id: 'document',
    title: 'Analyze document',
    description: 'Analyze this document and provide a comprehensive summary with key insights.',
    icon: <FileSpreadsheet size={17} className="text-[#D68B55]" />,
    prompt: 'Analyze this document and provide a comprehensive summary with key insights.',
  },
  {
    id: 'ideas',
    title: 'Brainstorm ideas',
    description: 'Brainstorm 10 innovative product ideas for AI-powered tools in 2026.',
    icon: <Lightbulb size={17} className="text-[#D68B55]" />,
    prompt: 'Brainstorm 10 innovative product ideas for AI-powered tools in 2026.',
  },
  {
    id: 'research',
    title: 'Research topic',
    description: 'Provide a comprehensive research overview on quantum computing and its applications.',
    icon: <Globe size={17} className="text-[#D68B55]" />,
    prompt: 'Provide a comprehensive research overview on quantum computing and its applications.',
  },
];

export const HomeView: React.FC<HomeViewProps> = ({
  onSendText,
  state,
  activeModel,
  activeVoice,
  deepSearchActive,
  onStartListening,
  onStopAudio,
  onOpenSettings,
  onToggleDeepSearch,
  disabled = false,
}) => {
  const [inputText, setInputText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [inputText]);

  const handleSend = () => {
    const trimmed = inputText.trim();
    if (!trimmed || disabled) return;
    onSendText(trimmed);
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isBusy = state === 'SPEAKING' || state === 'THINKING';
  const isListening = state === 'LISTENING';

  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col items-center justify-center pt-4 pb-12 px-4 animate-in fade-in duration-200">
      {/* Luminous AI Orb (Reference Image 3) */}
      <div className="mb-4">
        <VoiceOrb
          state={state}
          onClick={state === 'LISTENING' ? onStopAudio : onStartListening}
        />
      </div>

      {/* Active Model Status Indicator */}
      <div className="mb-3 flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--surface-primary)] border border-[var(--border)] text-xs text-[var(--text-secondary)] shadow-2xs">
        <Cpu size={12} className="text-[var(--accent)]" />
        <span className="font-medium text-[var(--text-primary)]">{activeModel}</span>
        <span className="text-[var(--text-tertiary)]">·</span>
        <span className="flex items-center gap-1">
          <Volume2 size={11} className="text-[var(--accent)]" />
          {activeVoice}
        </span>
      </div>

      {/* Greeting Heading (Reference Image 4) */}
      <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-[var(--text-primary)] mb-1 text-center">
        {getGreeting()}, Lukas
      </h1>
      <p className="text-sm sm:text-base text-[var(--text-secondary)] mb-7 text-center font-normal">
        What can I help you with today?
      </p>

      {/* Large Rounded Chat Composer (Reference Image 4 & 5) */}
      <div className="w-full max-w-2xl floating-input-card p-4 mb-7">
        <textarea
          ref={textareaRef}
          rows={2}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything, press Enter to send, or click the mic to speak..."
          disabled={disabled}
          className="w-full bg-transparent text-[15px] text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none resize-none leading-relaxed min-h-[50px] max-h-[140px] aura-scroller"
        />

        {/* Composer Bottom Row */}
        <div className="flex items-center justify-between pt-3 border-t border-[var(--border)] mt-2">
          {/* Left tools: Attachment, Web Search, Voice Mic */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => {}}
              title="Attach File or Context"
              className="p-1.5 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-secondary)] transition cursor-pointer"
            >
              <Paperclip size={16} />
            </button>

            <button
              type="button"
              onClick={() => onToggleDeepSearch(!deepSearchActive)}
              title={deepSearchActive ? 'Wikipedia Deep Search Active' : 'Enable Deep Search'}
              className={`p-1.5 rounded-lg transition cursor-pointer flex items-center gap-1 text-xs font-medium ${
                deepSearchActive
                  ? 'text-[#2563EB] bg-[#EFF6FF]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-secondary)]'
              }`}
            >
              <Globe size={15} />
              <span className="hidden sm:inline">Search</span>
            </button>

            <button
              type="button"
              onClick={() => {
                if (isListening) onStopAudio();
                else onStartListening();
              }}
              title={isListening ? 'Stop listening' : 'Start voice recognition (Faster-Whisper)'}
              className={`p-1.5 rounded-lg transition cursor-pointer ${
                isListening
                  ? 'text-white bg-[var(--status-error)] animate-pulse'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-secondary)]'
              }`}
            >
              <Mic size={16} />
            </button>
          </div>

          {/* Right tools: Model & Voice Persona Switcher, Send button */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onOpenSettings}
              className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--surface-secondary)] hover:bg-[var(--border)] text-[var(--text-primary)] transition cursor-pointer"
            >
              <span className="truncate max-w-[120px]">{activeModel}</span>
              <ChevronDown size={12} className="text-[var(--text-tertiary)]" />
            </button>

            <button
              type="button"
              onClick={onOpenSettings}
              title={`Voice: ${activeVoice}`}
              className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--surface-secondary)] hover:bg-[var(--border)] text-[var(--accent)] transition cursor-pointer"
            >
              <Volume2 size={12} />
              <span className="truncate max-w-[80px]">{activeVoice}</span>
            </button>

            {isBusy || isListening ? (
              <button
                type="button"
                onClick={onStopAudio}
                title="Stop"
                className="w-8 h-8 rounded-full bg-rose-500 hover:bg-rose-600 text-white flex items-center justify-center transition cursor-pointer shadow-2xs"
              >
                <Square size={13} fill="currentColor" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSend}
                disabled={!inputText.trim() || disabled}
                title="Send (Enter)"
                className="w-8 h-8 rounded-full bg-[var(--text-primary)] hover:bg-black text-[var(--surface-primary)] flex items-center justify-center transition disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer shadow-2xs"
              >
                <ArrowUp size={15} strokeWidth={2.4} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* QUICK START Cards (4 Cards matching Reference Image 4) */}
      <div className="w-full max-w-2xl">
        <div className="text-[11px] font-semibold tracking-wider text-[var(--text-secondary)] uppercase mb-3 ml-1">
          Quick Start
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          {QUICK_START_CARDS.map((card) => (
            <button
              key={card.id}
              type="button"
              onClick={() => onSendText(card.prompt)}
              className="quick-start-card p-4 text-left flex items-start gap-3.5 cursor-pointer group"
            >
              <div className="p-2 rounded-xl bg-[var(--surface-secondary)] group-hover:bg-[var(--accent-light)] transition shrink-0">
                {card.icon}
              </div>
              <div className="min-w-0">
                <div className="text-[13px] font-semibold text-[var(--text-primary)] group-hover:text-[var(--accent)] transition">
                  {card.title}
                </div>
                <div className="text-[12px] text-[var(--text-secondary)] leading-snug mt-0.5 line-clamp-2">
                  {card.description}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
