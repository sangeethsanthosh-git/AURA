import React from 'react';
import {
  Mic,
  Square,
  Radio,
  Sliders,
  CheckCircle2,
} from 'lucide-react';
import type { AssistantState, VoiceProfile } from '../hooks/useAuraSocket';

interface VoiceStudioViewProps {
  state: AssistantState;
  activeVoice: string;
  activeModel: string;
  availableVoices: VoiceProfile[];
  wakeWordActive: boolean;
  isConnected: boolean;
  onStartListening: () => void;
  onStopAudio: () => void;
  onSelectVoice: (voice: string) => void;
  onToggleWakeWord: (enabled: boolean) => void;
  onOpenSettings: () => void;
  onSendTestPhrase: (phrase: string) => void;
}

const TEST_PHRASES = [
  'Hello AURA, introduce yourself and explain what you can do.',
  'What are the three laws of robotics?',
  'Summarize the latest developments in quantum computing.',
  'Tell me an interesting historical fact about space exploration.',
];

export const VoiceStudioView: React.FC<VoiceStudioViewProps> = ({
  state,
  activeVoice,
  activeModel,
  availableVoices,
  wakeWordActive,
  isConnected,
  onStartListening,
  onStopAudio,
  onSelectVoice,
  onToggleWakeWord,
  onOpenSettings,
  onSendTestPhrase,
}) => {
  const isListening = state === 'LISTENING';
  const isSpeaking = state === 'SPEAKING';
  const isThinking = state === 'THINKING';
  const isBusy = isSpeaking || isThinking;

  const getStateBadge = () => {
    switch (state) {
      case 'LISTENING':
        return {
          label: 'Listening to Microphone...',
          color: 'text-rose-600 bg-rose-50 border-rose-200',
          dot: 'bg-rose-500 animate-ping',
        };
      case 'THINKING':
        return {
          label: 'Processing Neural Thought...',
          color: 'text-amber-600 bg-amber-50 border-amber-200',
          dot: 'bg-amber-500 animate-pulse',
        };
      case 'SPEAKING':
        return {
          label: 'Synthesizing & Speaking...',
          color: 'text-[var(--accent)] bg-[var(--accent-light)] border-[var(--accent)]/30',
          dot: 'bg-[var(--accent)]',
        };
      case 'ERROR':
        return {
          label: 'Audio Pipeline Error',
          color: 'text-rose-700 bg-rose-100 border-rose-300',
          dot: 'bg-rose-600',
        };
      case 'IDLE':
      default:
        return {
          label: 'Ready / Standby',
          color: 'text-emerald-700 bg-emerald-50 border-emerald-200',
          dot: 'bg-emerald-500',
        };
    }
  };

  const badge = getStateBadge();

  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col items-center justify-between h-full py-6 px-4 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="w-full flex items-center justify-between border-b border-[var(--border)] pb-4">
        <div>
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Voice Studio</h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Real-time Faster-Whisper STT & Neural Text-to-Speech Engine
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span
            title={isConnected ? 'Connected to local Ollama & FastAPI' : 'Offline'}
            className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-medium bg-[var(--surface-primary)] border border-[var(--border)] text-[var(--text-secondary)]"
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-[var(--status-success)]' : 'bg-[var(--status-error)]'}`} />
            <span>{activeModel}</span>
          </span>

          <button
            type="button"
            onClick={() => onToggleWakeWord(!wakeWordActive)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition cursor-pointer ${
              wakeWordActive
                ? 'bg-amber-50 border-amber-200 text-amber-800'
                : 'bg-[var(--surface-primary)] border-[var(--border)] text-[var(--text-secondary)]'
            }`}
          >
            <Radio size={13} className={wakeWordActive ? 'text-amber-600 animate-pulse' : ''} />
            <span>Hey Aura</span>
          </button>

          <button
            type="button"
            onClick={onOpenSettings}
            className="p-1.5 rounded-xl bg-[var(--surface-primary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer"
          >
            <Sliders size={15} />
          </button>
        </div>
      </div>

      {/* Center Stage: Tactile Push-to-Talk & Waveform Visualizer */}
      <div className="flex flex-col items-center justify-center my-auto py-8">
        {/* Animated Waveform Visualizer */}
        <div className="flex items-center justify-center gap-1.5 h-16 mb-8">
          {[0.2, 0.4, 0.6, 0.8, 1.0, 0.8, 0.6, 0.4, 0.2].map((scale, i) => (
            <div
              key={i}
              className={`w-1.5 rounded-full transition-all duration-300 ${
                isSpeaking || isListening
                  ? 'voice-wave-bar'
                  : 'bg-[var(--border-strong)] h-3'
              }`}
              style={{
                animationDelay: `${i * 0.12}s`,
                height: isSpeaking || isListening ? undefined : `${scale * 16}px`,
              }}
            />
          ))}
        </div>

        {/* Large Central Push-to-Talk Button */}
        <button
          type="button"
          onClick={() => {
            if (isListening || isBusy) onStopAudio();
            else onStartListening();
          }}
          className={`w-28 h-28 rounded-full flex flex-col items-center justify-center gap-1 transition-all duration-300 cursor-pointer shadow-lg ${
            isListening
              ? 'bg-rose-500 text-white ring-8 ring-rose-200 animate-pulse shadow-rose-500/30'
              : isBusy
              ? 'bg-amber-500 text-white ring-8 ring-amber-200 shadow-amber-500/30'
              : 'bg-[var(--surface-primary)] hover:bg-[var(--surface-secondary)] text-[var(--text-primary)] border-2 border-[var(--border-strong)] hover:border-[var(--accent)] hover:scale-105 shadow-md'
          }`}
        >
          {isListening ? (
            <>
              <Square size={28} fill="currentColor" />
              <span className="text-[10px] font-semibold uppercase tracking-wider">Stop</span>
            </>
          ) : isBusy ? (
            <>
              <Square size={28} fill="currentColor" />
              <span className="text-[10px] font-semibold uppercase tracking-wider">Interrupt</span>
            </>
          ) : (
            <>
              <Mic size={32} className="text-[var(--accent)]" />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                Push to Talk
              </span>
            </>
          )}
        </button>

        {/* Live State Badge */}
        <div className="mt-6 flex items-center gap-2">
          <div
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium border shadow-2xs ${badge.color}`}
          >
            <span className={`w-2 h-2 rounded-full ${badge.dot}`} />
            <span>{badge.label}</span>
          </div>
        </div>

        {/* Spacebar helper */}
        <p className="text-[11px] text-[var(--text-tertiary)] mt-3">
          Tip: Hold or press <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface-primary)] border border-[var(--border)] font-mono text-[10px]">Space</kbd> anywhere to talk
        </p>
      </div>

      {/* Bottom Section: Active Persona Selector & Quick Test Phrases */}
      <div className="w-full flex flex-col gap-4">
        {/* Persona Switcher Chips */}
        <div>
          <div className="text-[11px] font-semibold tracking-wider text-[var(--text-tertiary)] uppercase mb-2 flex items-center justify-between">
            <span>Voice Personas</span>
            <span className="text-[10px] text-[var(--accent)] font-medium">Active: {activeVoice}</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {availableVoices.slice(0, 6).map((v) => {
              const isSelected = activeVoice.toLowerCase() === v.name.toLowerCase();
              return (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => onSelectVoice(v.name)}
                  className={`p-2.5 rounded-xl border text-left flex items-center justify-between transition cursor-pointer ${
                    isSelected
                      ? 'bg-[var(--surface-primary)] border-[var(--accent)] shadow-xs'
                      : 'bg-[var(--surface-primary)]/70 hover:bg-[var(--surface-primary)] border-[var(--border)]'
                  }`}
                >
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs font-semibold text-[var(--text-primary)] truncate">
                      {v.name}
                    </span>
                    <span className="text-[10px] text-[var(--text-secondary)] truncate">
                      {v.gender} · {v.engine}
                    </span>
                  </div>
                  {isSelected && <CheckCircle2 size={14} className="text-[var(--accent)] shrink-0" />}
                </button>
              );
            })}
          </div>
        </div>

        {/* Quick Test Audio Prompts */}
        <div>
          <div className="text-[11px] font-semibold tracking-wider text-[var(--text-tertiary)] uppercase mb-2">
            Test Speech Synthesis
          </div>

          <div className="flex flex-wrap gap-2">
            {TEST_PHRASES.map((phrase, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onSendTestPhrase(phrase)}
                className="text-xs px-3 py-1.5 rounded-xl bg-[var(--surface-primary)] hover:bg-[var(--surface-secondary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer text-left truncate max-w-full"
              >
                "{phrase}"
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
