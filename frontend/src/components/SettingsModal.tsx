import React, { useState } from 'react';
import { X, Cpu, HardDrive, Volume2, CheckCircle2, Zap, Activity, Sparkles, Mail } from 'lucide-react';
import type { VoiceProfile } from '../hooks/useAuraSocket';
import { ResourceMonitorSection } from './ResourceMonitorSection';
import { PersonalitySettingsSection } from './PersonalitySettingsSection';
import { EmailNotificationsSection } from './EmailNotificationsSection';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeModel: string;
  onSelectModel: (model: string) => void;
  activeVoice: string;
  onSelectVoice: (voice: string) => void;
  availableVoices: VoiceProfile[];
  isConnected: boolean;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  activeModel,
  onSelectModel,
  activeVoice,
  onSelectVoice,
  availableVoices,
  isConnected,
}) => {
  const [tab, setTab] = useState<'voice' | 'personality' | 'email' | 'model' | 'resources'>('voice');
  const [selectedModel, setSelectedModel] = useState(activeModel);
  const [selectedVoice, setSelectedVoice] = useState(activeVoice);

  if (!isOpen) return null;

  const availableModels = [
    { id: 'llama3.2:3b', name: 'Llama 3.2 (3B)', desc: 'Active conversational LLM (Default)' },
    { id: 'qwen3:1.7b', name: 'Qwen 3 (1.7B)', desc: 'Ultra-lightweight fast local LLM' },
    { id: 'deepseek-r1:1.5b', name: 'DeepSeek R1 (1.5B)', desc: 'Local reasoning & thinking model' },
  ];

  const handleApply = () => {
    if (selectedModel !== activeModel) {
      onSelectModel(selectedModel);
    }
    if (selectedVoice !== activeVoice) {
      onSelectVoice(selectedVoice);
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-lg p-6 bg-white/95 border border-white/80 shadow-[0_20px_60px_rgba(235,110,65,0.22)] rounded-3xl flex flex-col gap-4 max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-black/[0.06] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#FF7E5F] to-[#FF5436] flex items-center justify-center text-white shadow-xs">
              <Cpu size={17} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-[#1F1C1A]">AURA Preferences</h2>
              <p className="text-[11px] text-[#8C7E75]">Audio profiles & AI model configuration</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full text-[#7A6E64] hover:text-[#1F1C1A] hover:bg-black/[0.05] transition cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Status Bar */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex items-center justify-between px-3 py-2 rounded-2xl bg-black/[0.03] border border-black/[0.05]">
            <span className="flex items-center gap-1.5 text-[#6B5E54]">
              <HardDrive size={13} className="text-[#FF7E5F]" />
              WebSocket
            </span>
            <span className={`font-semibold ${isConnected ? 'text-emerald-600' : 'text-rose-600'}`}>
              {isConnected ? 'Connected' : 'Offline'}
            </span>
          </div>
          <div className="flex items-center justify-between px-3 py-2 rounded-2xl bg-black/[0.03] border border-black/[0.05]">
            <span className="flex items-center gap-1.5 text-[#6B5E54]">
              <Volume2 size={13} className="text-[#FF7E5F]" />
              Voice
            </span>
            <span className="text-[#D44726] font-semibold truncate max-w-[100px]">{activeVoice}</span>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 p-1 bg-black/[0.03] rounded-2xl border border-black/[0.05] text-xs font-medium">
          <button
            type="button"
            onClick={() => setTab('voice')}
            className={`flex-1 py-1.5 rounded-xl flex items-center justify-center gap-1.5 transition cursor-pointer ${
              tab === 'voice'
                ? 'bg-white text-[#D44726] font-semibold shadow-xs border border-black/[0.04]'
                : 'text-[#7A6E64] hover:text-[#1F1C1A]'
            }`}
          >
            <Volume2 size={13} />
            Voice ({availableVoices.length})
          </button>
          <button
            type="button"
            onClick={() => setTab('personality')}
            className={`flex-1 py-1.5 rounded-xl flex items-center justify-center gap-1.5 transition cursor-pointer ${
              tab === 'personality'
                ? 'bg-white text-[#D44726] font-semibold shadow-xs border border-black/[0.04]'
                : 'text-[#7A6E64] hover:text-[#1F1C1A]'
            }`}
          >
            <Sparkles size={13} />
            Persona & Social
          </button>
          <button
            type="button"
            onClick={() => setTab('email')}
            className={`flex-1 py-1.5 rounded-xl flex items-center justify-center gap-1.5 transition cursor-pointer ${
              tab === 'email'
                ? 'bg-white text-[#D44726] font-semibold shadow-xs border border-black/[0.04]'
                : 'text-[#7A6E64] hover:text-[#1F1C1A]'
            }`}
          >
            <Mail size={13} />
            Email
          </button>
          <button
            type="button"
            onClick={() => setTab('model')}
            className={`flex-1 py-1.5 rounded-xl flex items-center justify-center gap-1.5 transition cursor-pointer ${
              tab === 'model'
                ? 'bg-white text-[#D44726] font-semibold shadow-xs border border-black/[0.04]'
                : 'text-[#7A6E64] hover:text-[#1F1C1A]'
            }`}
          >
            <Zap size={13} />
            LLM ({availableModels.length})
          </button>
          <button
            type="button"
            onClick={() => setTab('resources')}
            className={`flex-1 py-1.5 rounded-xl flex items-center justify-center gap-1.5 transition cursor-pointer ${
              tab === 'resources'
                ? 'bg-white text-[#D44726] font-semibold shadow-xs border border-black/[0.04]'
                : 'text-[#7A6E64] hover:text-[#1F1C1A]'
            }`}
          >
            <Activity size={13} />
            Resources
          </button>
        </div>

        {/* Tab 1: Voice Persona Selection */}
        {tab === 'voice' && (
          <div className="flex flex-col gap-2 overflow-y-auto max-h-[340px] pr-1 luminous-scroller">
            <div className="text-[11px] font-medium uppercase tracking-wider text-[#9E9086] px-1">
              Select AI Voice
            </div>
            <div className="flex flex-col gap-2">
              {availableVoices.map((v) => {
                const isSelected =
                  selectedVoice.toLowerCase() === v.id.toLowerCase() ||
                  selectedVoice.toLowerCase() === v.name.toLowerCase() ||
                  selectedVoice.toLowerCase() === v.speaker.toLowerCase();
                return (
                  <div
                    key={v.id}
                    onClick={() => setSelectedVoice(v.name)}
                    className={`p-3 rounded-2xl border cursor-pointer flex items-center justify-between transition-all ${
                      isSelected
                        ? 'border-[#FF7E5F] bg-[#FFF6F0] shadow-xs'
                        : 'border-black/[0.06] bg-white/70 hover:bg-black/[0.02]'
                    }`}
                  >
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-[#1F1C1A]">{v.name}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-black/[0.05] text-[#6E6056]">
                          {v.gender}
                        </span>
                        {v.badge && (
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                              v.engine === 'piper'
                                ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                : 'bg-[#FFF0E8] text-[#D44726] border border-[#FF7E5F]/30'
                            }`}
                          >
                            {v.badge}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-[#7A6E64]">{v.description}</div>
                    </div>
                    {isSelected && (
                      <CheckCircle2 size={18} className="text-[#FF5436] shrink-0 ml-2" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab 2: Personality & Social Behaviour */}
        {tab === 'personality' && <PersonalitySettingsSection />}

        {/* Tab 3: Email Notifications & Reminders */}
        {tab === 'email' && <EmailNotificationsSection />}

        {/* Tab 4: LLM Selection */}
        {tab === 'model' && (
          <div className="flex flex-col gap-2 overflow-y-auto max-h-[340px] pr-1 luminous-scroller">
            <div className="text-[11px] font-medium uppercase tracking-wider text-[#9E9086] px-1">
              Select Local Reasoning Model
            </div>
            <div className="flex flex-col gap-2">
              {availableModels.map((m) => (
                <div
                  key={m.id}
                  onClick={() => setSelectedModel(m.id)}
                  className={`p-3 rounded-2xl border cursor-pointer flex items-center justify-between transition-all ${
                    selectedModel === m.id
                      ? 'border-[#FF7E5F] bg-[#FFF6F0] shadow-xs'
                      : 'border-black/[0.06] bg-white/70 hover:bg-black/[0.02]'
                  }`}
                >
                  <div>
                    <div className="text-sm font-semibold text-[#1F1C1A]">{m.name}</div>
                    <div className="text-xs text-[#7A6E64]">{m.desc}</div>
                  </div>
                  {selectedModel === m.id && (
                    <CheckCircle2 size={18} className="text-[#FF5436] shrink-0" />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 3: Resource Monitor & Perception Cache */}
        {tab === 'resources' && <ResourceMonitorSection />}

        {/* Actions Footer */}
        <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-black/[0.06]">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-[#7A6E64] hover:text-[#1F1C1A] transition cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleApply}
            className="px-5 py-2 text-xs font-semibold rounded-xl bg-gradient-to-r from-[#FF7E5F] to-[#FF5436] hover:from-[#FF6F4E] hover:to-[#E53D20] text-white transition shadow-md shadow-[#FF7E5F]/25 cursor-pointer"
          >
            Apply Changes
          </button>
        </div>
      </div>
    </div>
  );
};
