import React, { useState } from 'react';
import {
  FileText,
  ListTodo,
  Layers,
  Sparkles,
  ChevronDown,
  X,
  Volume2,
  Cpu,
} from 'lucide-react';
import type { ChatMessage } from '../hooks/useAuraSocket';

interface WorkspaceNotesPanelProps {
  messages: ChatMessage[];
  activeModel: string;
  activeVoice: string;
  onClose: () => void;
}

export const WorkspaceNotesPanel: React.FC<WorkspaceNotesPanelProps> = ({
  messages,
  activeModel,
  activeVoice,
  onClose,
}) => {
  const [tab, setTab] = useState<'notes' | 'context' | 'plan'>('notes');

  // Extract key conversation takeaways
  const userMessages = messages.filter((m) => m.role === 'user');
  const assistantMessages = messages.filter((m) => m.role === 'assistant');

  return (
    <aside className="w-[340px] h-full bg-[#FAF7F2] border-l border-[#EBE4D8] flex flex-col justify-between p-4 shrink-0 select-none z-10 animate-in slide-in-from-right duration-200">
      <div className="flex flex-col h-full overflow-hidden">
        {/* Top Header: Version dropdown & Tabs (Image 3 style) */}
        <div className="flex items-center justify-between pb-3 border-b border-[#EBE4D8]">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-[#1C1917] bg-white px-2.5 py-1 rounded-lg border border-[#E8E2D6] shadow-2xs">
            <span>3.1 version</span>
            <ChevronDown size={12} className="text-[#A8A29E]" />
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={onClose}
              className="p-1 rounded-md text-[#A8A29E] hover:text-[#1C1917] hover:bg-black/[0.04] transition cursor-pointer"
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Tab Buttons (Image 3: [ Context | Plan | Notes ]) */}
        <div className="flex items-center gap-1 p-1 bg-[#EFE9DF] rounded-xl my-3 text-xs font-medium">
          <button
            type="button"
            onClick={() => setTab('context')}
            className={`flex-1 py-1 rounded-lg flex items-center justify-center gap-1 transition cursor-pointer ${
              tab === 'context'
                ? 'bg-white text-[#1C1917] shadow-xs font-semibold'
                : 'text-[#78716C] hover:text-[#1C1917]'
            }`}
          >
            <Layers size={12} />
            <span>Context</span>
          </button>
          <button
            type="button"
            onClick={() => setTab('plan')}
            className={`flex-1 py-1 rounded-lg flex items-center justify-center gap-1 transition cursor-pointer ${
              tab === 'plan'
                ? 'bg-white text-[#1C1917] shadow-xs font-semibold'
                : 'text-[#78716C] hover:text-[#1C1917]'
            }`}
          >
            <ListTodo size={12} />
            <span>Plan</span>
          </button>
          <button
            type="button"
            onClick={() => setTab('notes')}
            className={`flex-1 py-1 rounded-lg flex items-center justify-center gap-1 transition cursor-pointer ${
              tab === 'notes'
                ? 'bg-white text-[#1C1917] shadow-xs font-semibold'
                : 'text-[#78716C] hover:text-[#1C1917]'
            }`}
          >
            <FileText size={12} />
            <span>Notes</span>
          </button>
        </div>

        {/* Updated Automatically Pill (Image 3 style) */}
        <div className="flex items-center gap-1.5 text-[11px] text-[#A8A29E] mb-3 px-1">
          <Sparkles size={11} className="text-[#D97706]" />
          <span>Updated automatically</span>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto aura-scroller pr-1 flex flex-col gap-4 text-xs">
          {tab === 'notes' && (
            <>
              <div>
                <h4 className="font-semibold text-[#1C1917] text-[13px] mb-1">
                  1. Core Architecture
                </h4>
                <p className="text-[#78716C] leading-relaxed">
                  Local-first AI conversational engine powered by Faster-Whisper, local Ollama LLMs, and real-time Edge-TTS neural voices.
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-[#1C1917] text-[13px] mb-1">
                  2. Active Engine Pipeline
                </h4>
                <div className="flex flex-col gap-1.5 mt-1">
                  <div className="p-2 rounded-xl bg-white border border-[#E8E2D6] flex items-center justify-between">
                    <span className="flex items-center gap-1 text-[#44403C]">
                      <Cpu size={12} className="text-[#D97706]" />
                      Model
                    </span>
                    <span className="font-mono text-[11px] font-semibold text-[#1C1917]">{activeModel}</span>
                  </div>
                  <div className="p-2 rounded-xl bg-white border border-[#E8E2D6] flex items-center justify-between">
                    <span className="flex items-center gap-1 text-[#44403C]">
                      <Volume2 size={12} className="text-[#EA580C]" />
                      Voice Persona
                    </span>
                    <span className="font-medium text-[11px] text-[#1C1917]">{activeVoice}</span>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-[#1C1917] text-[13px] mb-1">
                  3. Key Topics Explored
                </h4>
                {userMessages.length === 0 ? (
                  <p className="text-[#A8A29E] italic">
                    Start speaking or select a topic to populate live synthesis.
                  </p>
                ) : (
                  <ul className="flex flex-col gap-1.5 text-[#57534E]">
                    {userMessages.slice(-4).map((msg, idx) => (
                      <li key={idx} className="flex items-start gap-1.5 bg-white p-2 rounded-xl border border-[#E8E2D6]">
                        <span className="text-[#D97706] font-bold">·</span>
                        <span className="truncate">{msg.content}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}

          {tab === 'context' && (
            <div className="flex flex-col gap-3">
              <div>
                <h4 className="font-semibold text-[#1C1917] text-[13px] mb-1">
                  Current Session Context
                </h4>
                <p className="text-[#78716C] leading-relaxed">
                  Messages in session: {messages.length} ({userMessages.length} user prompts, {assistantMessages.length} assistant replies).
                </p>
              </div>
              <div className="p-3 bg-white rounded-xl border border-[#E8E2D6] text-[#78716C] leading-relaxed">
                Context window retention is maintained across session memory with live speech synthesis active.
              </div>
            </div>
          )}

          {tab === 'plan' && (
            <div className="flex flex-col gap-3">
              <div>
                <h4 className="font-semibold text-[#1C1917] text-[13px] mb-1">
                  Execution Plan
                </h4>
                <p className="text-[#78716C] leading-relaxed">
                  Step 1: Input text or voice recognition.
                  <br />
                  Step 2: Stream local LLM reasoning.
                  <br />
                  Step 3: Synthesize real-time audio playback.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
