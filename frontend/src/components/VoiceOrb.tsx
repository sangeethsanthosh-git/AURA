import React from 'react';
import type { AssistantState } from '../hooks/useAuraSocket';
import { Mic, Sparkles, Brain, Volume2, AlertCircle } from 'lucide-react';

interface VoiceOrbProps {
  state: AssistantState;
  onClick?: () => void;
}

export const VoiceOrb: React.FC<VoiceOrbProps> = ({ state, onClick }) => {
  const getStatusInfo = (s: AssistantState) => {
    switch (s) {
      case 'LISTENING':
        return {
          label: 'Listening...',
          icon: <Mic size={13} className="text-[#FF5238] animate-pulse" />,
          dotClass: 'bg-[#FF5238] animate-ping',
          badgeClass: 'border-[#FF5238]/30 bg-white/80 text-[#D82218] shadow-sm shadow-[#FF5238]/15',
        };
      case 'THINKING':
        return {
          label: 'Thinking...',
          icon: <Brain size={13} className="text-[#E91E63] animate-pulse" />,
          dotClass: 'bg-[#E91E63] animate-pulse',
          badgeClass: 'border-[#E91E63]/30 bg-white/80 text-[#C2185B] shadow-sm shadow-[#E91E63]/15',
        };
      case 'SPEAKING':
        return {
          label: 'Speaking...',
          icon: <Volume2 size={13} className="text-[#FF7E40]" />,
          dotClass: 'bg-[#FF7E40]',
          badgeClass: 'border-[#FF7E40]/30 bg-white/80 text-[#E83F24] shadow-sm shadow-[#FF7E40]/15',
        };
      case 'ERROR':
        return {
          label: 'System Alert',
          icon: <AlertCircle size={13} className="text-rose-600" />,
          dotClass: 'bg-rose-500',
          badgeClass: 'border-rose-400/40 bg-white/80 text-rose-700 shadow-sm',
        };
      case 'IDLE':
      default:
        return {
          label: 'AURA Standby',
          icon: <Sparkles size={13} className="text-[#FF7E5F]" />,
          dotClass: 'bg-[#FF7E5F]',
          badgeClass: 'border-white/80 bg-white/60 text-[#6B5E55] hover:bg-white/85',
        };
    }
  };

  const status = getStatusInfo(state);

  return (
    <div
      className="flex flex-col items-center justify-center cursor-pointer select-none group transition-transform duration-300 hover:scale-[1.02]"
      onClick={onClick}
      title={state === 'IDLE' ? 'Click to Speak' : 'Click to Interrupt'}
    >
      <div className={`orb-container state-${state}`}>
        {/* Animated Sonar Rings for Listening */}
        {state === 'LISTENING' && (
          <>
            <div className="orb-ring" style={{ animationDelay: '0s' }} />
            <div className="orb-ring" style={{ animationDelay: '0.6s' }} />
            <div className="orb-ring" style={{ animationDelay: '1.2s' }} />
          </>
        )}

        {/* Central Luminous Sunset Orb Core */}
        <div className="orb-core flex items-center justify-center">
          {/* Waveform indicator when assistant is speaking */}
          {state === 'SPEAKING' && (
            <div className="wave-bars">
              <div className="wave-bar" style={{ animationDelay: '0.1s' }} />
              <div className="wave-bar" style={{ animationDelay: '0.3s' }} />
              <div className="wave-bar" style={{ animationDelay: '0.5s' }} />
              <div className="wave-bar" style={{ animationDelay: '0.2s' }} />
              <div className="wave-bar" style={{ animationDelay: '0.4s' }} />
            </div>
          )}
        </div>
      </div>

      {/* Chic Frosted Status Pill Badge */}
      <div className="mt-4">
        <div
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium tracking-wide backdrop-blur-md border transition-all duration-200 ${status.badgeClass}`}
        >
          {status.icon}
          <span>{status.label}</span>
          <span className={`w-1.5 h-1.5 rounded-full ml-0.5 ${status.dotClass}`} />
        </div>
      </div>
    </div>
  );
};
