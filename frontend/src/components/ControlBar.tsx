import React, { useState, useRef, useEffect } from 'react';
import {
  Mic,
  Square,
  ArrowUp,
  Plus,
  ChevronDown,
  Globe,
  Radio,
  Volume2,
  Sparkles,
} from 'lucide-react';
import type { AssistantState } from '../hooks/useAuraSocket';

interface ControlBarProps {
  state: AssistantState;
  activeModel?: string;
  activeVoice?: string;
  deepSearchActive?: boolean;
  wakeWordActive?: boolean;
  onStartListening: () => void;
  onStopAudio: () => void;
  onSendText: (text: string) => void;
  onOpenSettings: () => void;
  onClear: () => void;
  onToggleDeepSearch?: (enabled: boolean) => void;
  onToggleWakeWord?: (enabled: boolean) => void;
  disabled?: boolean;
}

export const ControlBar: React.FC<ControlBarProps> = ({
  state,
  activeModel = 'llama3.2:3b',
  activeVoice = 'Aria',
  deepSearchActive = true,
  wakeWordActive = true,
  onStartListening,
  onStopAudio,
  onSendText,
  onOpenSettings,
  onClear,
  onToggleDeepSearch,
  onToggleWakeWord,
  disabled = false,
}) => {
  const [textInput, setTextInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Auto-resize textarea height as content changes
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 110)}px`;
    }
  }, [textInput]);

  const handleSend = () => {
    const trimmed = textInput.trim();
    if (!trimmed || disabled) return;

    // Interrupt any active speech/thinking before sending new prompt
    if (state === 'SPEAKING' || state === 'THINKING') {
      onStopAudio();
    }
    onSendText(trimmed);
    setTextInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
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
    <div className="w-full max-w-2xl px-3 flex flex-col items-center">
      {/* Floating Luminous Pill Bar (Inspired by Reference Images 1 & 2) */}
      <div className="w-full luminous-pill-input rounded-[30px] p-2.5 sm:p-3 transition-all duration-300">
        {/* Top Input Area with Sparkle Icon Badge */}
        <div className="flex items-center gap-2.5 px-2 pt-1 pb-1">
          {/* Orange-Gradient Sparkle Icon Box (as in Reference Image 1) */}
          <div
            className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#FF7E5F] via-[#FF926B] to-[#FF5436] flex items-center justify-center shrink-0 shadow-md shadow-[#FF7E5F]/25 text-white"
            title="AURA Voice Assistant"
          >
            <Sparkles size={16} strokeWidth={2.4} />
          </div>

          {/* Text Input Area with warm caret */}
          <div className="flex-1 relative flex items-center">
            <textarea
              ref={textareaRef}
              rows={1}
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isListening
                  ? 'Listening to your voice... (Click mic to stop)'
                  : isBusy
                  ? 'AURA is answering... (Type to ask next)'
                  : 'Ask me anything, explore ideas, or press mic...'
              }
              disabled={disabled}
              className="w-full bg-transparent text-[#221E1B] placeholder-[#9E9086] focus:outline-none text-[15px] resize-none leading-relaxed min-h-[26px] max-h-[110px] luminous-scroller caret-[#FF6B4A]"
            />
          </div>

          {/* Right Actions: Mic & Circular Send/Stop Button */}
          <div className="flex items-center gap-1.5 shrink-0">
            {/* Microphone Button */}
            <button
              type="button"
              onClick={() => {
                if (isListening) {
                  onStopAudio();
                } else if (isBusy) {
                  onStopAudio();
                  onStartListening();
                } else {
                  onStartListening();
                }
              }}
              disabled={disabled}
              title={
                isListening
                  ? 'Listening... Click to stop'
                  : 'Click to Speak (or press Spacebar)'
              }
              className={`p-2 rounded-full transition-all duration-200 cursor-pointer ${
                isListening
                  ? 'text-white bg-gradient-to-r from-[#FF5436] to-[#FF7E5F] ring-4 ring-[#FF7E5F]/30 animate-pulse shadow-md shadow-[#FF5436]/30'
                  : 'text-[#7D7066] hover:text-[#24201D] hover:bg-white/80'
              }`}
            >
              <Mic size={18} />
            </button>

            {/* Circular Action / Send / Stop Button (Image 2 style) */}
            {isBusy || isListening ? (
              <button
                type="button"
                onClick={onStopAudio}
                title={isListening ? 'Cancel Listening' : 'Stop Speaking'}
                className="w-9 h-9 rounded-full bg-rose-500 hover:bg-rose-600 text-white transition shadow-md shadow-rose-500/25 flex items-center justify-center cursor-pointer"
              >
                <Square size={13} fill="currentColor" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSend}
                disabled={!textInput.trim() || disabled}
                title="Send message (Enter)"
                className="w-9 h-9 rounded-full bg-[#1F1C1A] hover:bg-[#342F2B] text-white transition shadow-md shadow-black/15 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center cursor-pointer"
              >
                <ArrowUp size={16} strokeWidth={2.4} />
              </button>
            )}
          </div>
        </div>

        {/* Bottom Filter & Feature Pills Row */}
        <div className="flex flex-wrap items-center justify-between pt-2 px-1 border-t border-black/[0.06] mt-1 gap-1.5 text-xs text-[#7A6E65]">
          {/* Left Feature Controls */}
          <div className="flex flex-wrap items-center gap-1.5">
            {/* New Conversation (+) */}
            <button
              type="button"
              onClick={onClear}
              title="New Conversation (+)"
              className="p-1 rounded-full text-[#7A6E65] hover:text-[#1F1C1A] hover:bg-white/90 transition cursor-pointer"
            >
              <Plus size={15} />
            </button>

            {/* Model Pill */}
            <button
              type="button"
              onClick={onOpenSettings}
              title="Change Ollama Model"
              className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-white/70 hover:bg-white text-[#4A4038] border border-black/[0.08] hover:border-black/[0.15] transition shadow-xs cursor-pointer"
            >
              <span className="truncate max-w-[110px]">{activeModel}</span>
              <ChevronDown size={11} className="text-[#A3968D]" />
            </button>

            {/* Voice Persona Pill */}
            <button
              type="button"
              onClick={onOpenSettings}
              title={`Active Voice: ${activeVoice} (Click to change voice)`}
              className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#FFF3EC] hover:bg-[#FFEAE0] text-[#D44726] border border-[#FF7E5F]/30 hover:border-[#FF7E5F]/50 transition shadow-xs cursor-pointer"
            >
              <Volume2 size={11} className="text-[#FF6B4A]" />
              <span className="truncate max-w-[85px]">{activeVoice}</span>
              <ChevronDown size={11} className="text-[#FF7E5F]" />
            </button>

            {/* Wikipedia Deep Search Toggle */}
            {onToggleDeepSearch && (
              <button
                type="button"
                onClick={() => onToggleDeepSearch(!deepSearchActive)}
                title={
                  deepSearchActive
                    ? 'Wikipedia Deep Search ON (Click to disable)'
                    : 'Wikipedia Deep Search OFF (Click to enable)'
                }
                className={`flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium border transition shadow-xs cursor-pointer ${
                  deepSearchActive
                    ? 'bg-[#EBF5FF] border-[#60A5FA]/40 text-[#1D4ED8]'
                    : 'bg-white/60 border-black/[0.07] text-[#8C7F75]'
                }`}
              >
                <Globe size={11} className={deepSearchActive ? 'text-[#2563EB]' : 'text-[#A3968D]'} />
                <span>Deep Search</span>
              </button>
            )}

            {/* Wake Word Indicator */}
            {onToggleWakeWord && (
              <button
                type="button"
                onClick={() => onToggleWakeWord(!wakeWordActive)}
                title={
                  wakeWordActive
                    ? 'Wake-word "AURA" active: say "AURA" anytime (Click to mute)'
                    : 'Wake-word disabled (Click to activate)'
                }
                className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border transition shadow-xs cursor-pointer ${
                  wakeWordActive
                    ? 'bg-[#FFF7ED] border-[#FB923C]/40 text-[#C2410C]'
                    : 'bg-white/50 border-black/[0.07] text-[#9E9086]'
                }`}
              >
                <Radio
                  size={11}
                  className={wakeWordActive ? 'text-[#EA580C] animate-pulse' : 'text-[#A3968D]'}
                />
                <span>Hey Aura</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
