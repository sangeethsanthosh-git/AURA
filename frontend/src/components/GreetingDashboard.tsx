import React, { useState, useRef, useEffect } from 'react';
import {
  Code,
  FileText,
  Sparkles,
  Globe,
  Mic,
  ArrowUp,
  Plus,
  ChevronDown,
  Volume2,
  Radio,
  Square,
} from 'lucide-react';
import type { AssistantState } from '../hooks/useAuraSocket';

interface GreetingDashboardProps {
  onSendText: (text: string) => void;
  state: AssistantState;
  activeModel: string;
  activeVoice: string;
  deepSearchActive: boolean;
  wakeWordActive: boolean;
  onStartListening: () => void;
  onStopAudio: () => void;
  onOpenSettings: () => void;
  onToggleDeepSearch: (enabled: boolean) => void;
  onToggleWakeWord: (enabled: boolean) => void;
  disabled?: boolean;
}

const QUICK_START_ITEMS = [
  {
    icon: <Code size={18} className="text-[#D97706]" />,
    title: 'Write a script',
    subtitle: 'Write a TypeScript script that fetches data from an API and processes it.',
    prompt: 'Write a TypeScript script that fetches data from a REST API and processes it cleanly with error handling.',
  },
  {
    icon: <FileText size={18} className="text-[#EA580C]" />,
    title: 'Analyze document',
    subtitle: 'Analyze this document and provide a comprehensive summary with key insights.',
    prompt: 'Provide a comprehensive summary and key insights on quantum computing and fault-tolerant algorithms.',
  },
  {
    icon: <Sparkles size={18} className="text-[#CA8A04]" />,
    title: 'Brainstorm ideas',
    subtitle: 'Brainstorm 10 innovative product ideas for AI-powered tools in 2026.',
    prompt: 'Brainstorm 10 innovative, practical product ideas for AI-powered developer tools in 2026.',
  },
  {
    icon: <Globe size={18} className="text-[#2563EB]" />,
    title: 'Research topic',
    subtitle: 'Provide a comprehensive research overview on quantum computing and its applications.',
    prompt: 'Search Wikipedia and provide an in-depth research overview of Apollo 11 mission history.',
  },
];

export const GreetingDashboard: React.FC<GreetingDashboardProps> = ({
  onSendText,
  state,
  activeModel,
  activeVoice,
  deepSearchActive,
  wakeWordActive,
  onStartListening,
  onStopAudio,
  onOpenSettings,
  onToggleDeepSearch,
  onToggleWakeWord,
  disabled = false,
}) => {
  const [inputText, setInputText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Time-aware greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning, Lukas';
    if (hour < 17) return 'Good afternoon, Lukas';
    return 'Good evening, Lukas';
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
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
    <div className="w-full max-w-2xl mx-auto flex flex-col items-center justify-center pt-8 pb-12 px-4 animate-in fade-in duration-300">
      {/* Top Centered Subtle Badge (Image 1 style: Pro Plan  Upgrade) */}
      <div className="mb-6 flex items-center gap-2 px-3 py-1 rounded-full bg-white/70 backdrop-blur-md border border-[#E8E2D6] text-xs font-medium text-[#78716C] shadow-2xs">
        <span>Pro Plan</span>
        <button
          type="button"
          onClick={onOpenSettings}
          className="text-[#D97706] hover:text-[#B45309] font-semibold cursor-pointer"
        >
          Upgrade
        </button>
      </div>

      {/* Large Greeting Heading (Image 1 style: "Good afternoon, Lukas") */}
      <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-[#1C1917] mb-8 text-center">
        {getGreeting()}
      </h1>

      {/* Prominent Floating Input Card (Image 1 style) */}
      <div className="w-full floating-input-card p-4 mb-10">
        <textarea
          ref={textareaRef}
          rows={2}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="How can I help you today?"
          disabled={disabled}
          className="w-full bg-transparent text-[16px] text-[#1C1917] placeholder-[#A8A29E] focus:outline-none resize-none leading-relaxed min-h-[50px] max-h-[140px] aura-scroller"
        />

        {/* Input Card Bottom Row: Tools on left, Model & Send on right */}
        <div className="flex items-center justify-between pt-3 border-t border-[#F2ECE3] mt-2">
          {/* Left Tools: (+), (Deep Search), (Mic), (Hey Aura) */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setInputText('')}
              title="Clear text / Attach"
              className="p-1.5 rounded-lg text-[#78716C] hover:text-[#1C1917] hover:bg-[#F5EFE6] transition cursor-pointer"
            >
              <Plus size={17} />
            </button>

            {/* Deep Search Wikipedia toggle */}
            <button
              type="button"
              onClick={() => onToggleDeepSearch(!deepSearchActive)}
              title={deepSearchActive ? 'Deep Search ON' : 'Deep Search OFF'}
              className={`p-1.5 rounded-lg transition cursor-pointer ${
                deepSearchActive
                  ? 'text-[#2563EB] bg-[#EFF6FF]'
                  : 'text-[#78716C] hover:text-[#1C1917] hover:bg-[#F5EFE6]'
              }`}
            >
              <Globe size={16} />
            </button>

            {/* Microphone Button */}
            <button
              type="button"
              onClick={() => {
                if (isListening) onStopAudio();
                else onStartListening();
              }}
              title={isListening ? 'Stop listening' : 'Speak with Faster-Whisper'}
              className={`p-1.5 rounded-lg transition cursor-pointer ${
                isListening
                  ? 'text-white bg-[#EA580C] ring-2 ring-[#EA580C]/30 animate-pulse'
                  : 'text-[#78716C] hover:text-[#1C1917] hover:bg-[#F5EFE6]'
              }`}
            >
              <Mic size={16} />
            </button>

            {/* Wake Word "Hey Aura" toggle */}
            <button
              type="button"
              onClick={() => onToggleWakeWord(!wakeWordActive)}
              title={wakeWordActive ? 'Wake word "AURA" active' : 'Wake word muted'}
              className={`p-1.5 rounded-lg transition cursor-pointer ${
                wakeWordActive
                  ? 'text-[#D97706] bg-[#FEF3C7]'
                  : 'text-[#A8A29E] hover:text-[#1C1917] hover:bg-[#F5EFE6]'
              }`}
            >
              <Radio size={15} />
            </button>
          </div>

          {/* Right Tools: Model Pill, Voice Pill & Circular Send Button */}
          <div className="flex items-center gap-2">
            {/* Model Selector Pill (Image 1 style: Axiom Ultra 3.1 ⌵) */}
            <button
              type="button"
              onClick={onOpenSettings}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-[#44403C] hover:bg-[#F5EFE6] transition cursor-pointer"
            >
              <span>{activeModel}</span>
              <ChevronDown size={13} className="text-[#A8A29E]" />
            </button>

            {/* Voice Pill */}
            <button
              type="button"
              onClick={onOpenSettings}
              title={`Voice: ${activeVoice}`}
              className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-[#FAF6F0] border border-[#E8E2D6] text-[#78716C] hover:text-[#1C1917] transition cursor-pointer"
            >
              <Volume2 size={12} className="text-[#EA580C]" />
              <span>{activeVoice}</span>
            </button>

            {/* Circular Send / Stop Button */}
            {isBusy || isListening ? (
              <button
                type="button"
                onClick={onStopAudio}
                title="Stop"
                className="w-8 h-8 rounded-full bg-rose-500 hover:bg-rose-600 text-white flex items-center justify-center transition shadow-xs cursor-pointer"
              >
                <Square size={13} fill="currentColor" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSend}
                disabled={!inputText.trim() || disabled}
                title="Send (Enter)"
                className="w-8 h-8 rounded-full bg-[#1C1917] hover:bg-[#292524] text-white flex items-center justify-center transition shadow-xs disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
              >
                <ArrowUp size={15} strokeWidth={2.4} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* QUICK START Section (Image 1 style) */}
      <div className="w-full">
        <div className="text-[11px] font-semibold tracking-wider text-[#A8A29E] uppercase mb-3 ml-1">
          Quick Start
        </div>

        {/* 2x2 Grid of Cards (Image 1 style) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {QUICK_START_ITEMS.map((item, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onSendText(item.prompt)}
              className="quick-start-card p-4 text-left flex items-start gap-3 cursor-pointer group"
            >
              <div className="w-8 h-8 rounded-xl bg-[#FAF6F0] flex items-center justify-center shrink-0 border border-[#EDE7DE] group-hover:scale-105 transition">
                {item.icon}
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-[13px] font-semibold text-[#1C1917] group-hover:text-[#0C0A09]">
                  {item.title}
                </span>
                <span className="text-[11px] text-[#78716C] leading-snug mt-0.5 line-clamp-2">
                  {item.subtitle}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
