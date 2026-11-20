import React, { useState, useEffect } from 'react';
import {
  Smile,
  GraduationCap,
  MessageCircle,
  Briefcase,
  Heart,
  Flame,
  Check,
  RotateCcw,
  Sparkles,
  Sliders,
  ShieldCheck,
} from 'lucide-react';

export interface PersonalitySettingsData {
  default_profile: string;
  current_profile: string;
  is_temporary_override: boolean;
  auto_switch_enabled: boolean;
  humor_intensity: number;
  sarcasm_intensity: number;
  formality: number;
  explanation_depth: 'concise' | 'balanced' | 'in_depth';
  proactivity: number;
}

const PROFILES = [
  {
    id: 'friend',
    name: 'Friend',
    icon: Smile,
    color: 'from-amber-400 to-orange-500',
    borderColor: 'border-orange-300',
    activeBg: 'bg-orange-500/10',
    textColor: 'text-orange-600',
    desc: 'Casual, funny & approachable. Light teasing & humorous observations.',
    companionMood: 'happy',
    tone: 'Warm, conversational & relaxed',
  },
  {
    id: 'teacher',
    name: 'Teacher',
    icon: GraduationCap,
    color: 'from-blue-500 to-indigo-600',
    borderColor: 'border-blue-300',
    activeBg: 'bg-blue-500/10',
    textColor: 'text-blue-600',
    desc: 'Patient & structured. Explains from fundamentals with analogies.',
    companionMood: 'think',
    tone: 'Instructive, clear & encouraging',
  },
  {
    id: 'normal',
    name: 'Normal',
    icon: MessageCircle,
    color: 'from-slate-400 to-stone-600',
    borderColor: 'border-stone-300',
    activeBg: 'bg-stone-500/10',
    textColor: 'text-stone-700',
    desc: 'Everyday natural companion. Zero artificial enthusiasm or pretense.',
    companionMood: 'neutral',
    tone: 'Balanced, honest & direct',
  },
  {
    id: 'professional',
    name: 'Professional',
    icon: Briefcase,
    color: 'from-emerald-500 to-teal-700',
    borderColor: 'border-emerald-300',
    activeBg: 'bg-emerald-500/10',
    textColor: 'text-emerald-700',
    desc: 'Direct & task-oriented. Minimal banter, maximal accuracy & speed.',
    companionMood: 'neutral',
    tone: 'Crisp, concise & structured',
  },
  {
    id: 'supportive',
    name: 'Supportive',
    icon: Heart,
    color: 'from-rose-400 to-pink-600',
    borderColor: 'border-rose-300',
    activeBg: 'bg-rose-500/10',
    textColor: 'text-rose-600',
    desc: 'Patient & empathetic listener. Validates feelings with zero toxic positivity.',
    companionMood: 'gentle',
    tone: 'Compassionate, gentle & calm',
  },
  {
    id: 'mischievous',
    name: 'Mischievous',
    icon: Flame,
    color: 'from-purple-500 to-fuchsia-600',
    borderColor: 'border-purple-300',
    activeBg: 'bg-purple-500/10',
    textColor: 'text-purple-600',
    desc: 'Witty comebacks, playful trolling & sarcasm. Never hostile.',
    companionMood: 'wink',
    tone: 'Playful, snappy & sarcastic',
  },
];

export const PersonalitySettingsSection: React.FC = () => {
  const [settings, setSettings] = useState<PersonalitySettingsData>({
    default_profile: 'normal',
    current_profile: 'normal',
    is_temporary_override: false,
    auto_switch_enabled: true,
    humor_intensity: 50,
    sarcasm_intensity: 25,
    formality: 40,
    explanation_depth: 'balanced',
    proactivity: 30,
  });

  const [saving, setSaving] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  const fetchSettings = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/personality');
      if (res.ok) {
        const data = await res.json();
        if (data.settings) {
          setSettings(data.settings);
        }
      }
    } catch (e) {
      console.debug('Failed to fetch personality settings:', e);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleProfileSelect = async (profileId: string, setAsDefault: boolean = false) => {
    setSaving(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/personality/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: profileId, temporary: !setAsDefault }),
      });
      if (res.ok) {
        const data = await res.json();
        setSettings(data.settings);
        setNotification(
          setAsDefault
            ? `Set ${profileId.toUpperCase()} as permanent default personality.`
            : `Switched to ${profileId.toUpperCase()} persona.`
        );
        setTimeout(() => setNotification(null), 3000);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateSliders = async (partial: Partial<PersonalitySettingsData>) => {
    const updated = { ...settings, ...partial };
    setSettings(updated);
    try {
      await fetch('http://127.0.0.1:8000/api/personality', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(partial),
      });
    } catch (e) {
      console.error('Failed to update personality settings:', e);
    }
  };

  const handleResetToDefault = async () => {
    setSaving(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/personality/reset', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSettings(data.settings);
        setNotification(`Restored default ${data.settings.default_profile.toUpperCase()} persona.`);
        setTimeout(() => setNotification(null), 3000);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const activeProfileObj = PROFILES.find((p) => p.id === settings.current_profile) || PROFILES[2];

  return (
    <div className="flex flex-col gap-4 overflow-y-auto max-h-[380px] pr-1 luminous-scroller text-stone-800">
      {/* Toast Notification */}
      {notification && (
        <div className="p-2.5 px-3 bg-gradient-to-r from-orange-500/15 to-amber-500/10 border border-orange-500/20 rounded-xl text-xs font-medium text-orange-800 flex items-center justify-between animate-in fade-in">
          <span>{notification}</span>
          <Check className="w-3.5 h-3.5 text-orange-600" />
        </div>
      )}

      {/* Header Info Banner */}
      <div className="flex items-center justify-between p-3 bg-white/70 backdrop-blur-sm border border-stone-200/80 rounded-2xl shadow-xs">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl bg-gradient-to-br ${activeProfileObj.color} text-white shadow-sm`}>
            <activeProfileObj.icon className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-stone-900 capitalize">
                {settings.current_profile} Mode
              </span>
              {settings.is_temporary_override && (
                <span className="px-1.5 py-0.5 text-[9px] font-semibold bg-amber-100 text-amber-700 rounded-md border border-amber-300">
                  Temporary Override
                </span>
              )}
              {settings.current_profile === settings.default_profile && !settings.is_temporary_override && (
                <span className="px-1.5 py-0.5 text-[9px] font-semibold bg-emerald-100 text-emerald-700 rounded-md border border-emerald-300">
                  Default Persona
                </span>
              )}
            </div>
            <p className="text-[11px] text-stone-500 mt-0.5">{activeProfileObj.tone}</p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleResetToDefault}
          disabled={saving}
          title="Reset to default personality"
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium text-stone-600 hover:text-stone-900 bg-stone-100 hover:bg-stone-200/70 border border-stone-200 rounded-xl transition cursor-pointer"
        >
          <RotateCcw className="w-3 h-3 text-stone-500" />
          Reset
        </button>
      </div>

      {/* 6 Personality Profiles Grid */}
      <div className="flex flex-col gap-2">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-stone-500 px-1 flex items-center justify-between">
          <span>Social Personality Profiles</span>
          <span className="text-[10px] lowercase text-stone-400 font-normal">click to switch</span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {PROFILES.map((prof) => {
            const isActive = settings.current_profile === prof.id;
            const isDefault = settings.default_profile === prof.id;
            const Icon = prof.icon;

            return (
              <div
                key={prof.id}
                onClick={() => handleProfileSelect(prof.id, false)}
                className={`relative p-2.5 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between ${
                  isActive
                    ? `bg-white border-orange-500 shadow-sm ring-1 ring-orange-500/20`
                    : 'bg-white/60 hover:bg-white border-stone-200/70 hover:border-stone-300 shadow-2xs'
                }`}
              >
                <div className="flex items-start justify-between gap-1 mb-1.5">
                  <div className="flex items-center gap-2">
                    <div className={`p-1.5 rounded-lg bg-gradient-to-br ${prof.color} text-white shadow-2xs`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <span className="text-xs font-semibold text-stone-800">{prof.name}</span>
                  </div>

                  <div className="flex items-center gap-1">
                    {isDefault && (
                      <span className="text-[9px] px-1.5 py-0.2 bg-stone-100 text-stone-600 font-medium rounded border border-stone-200">
                        Default
                      </span>
                    )}
                    {isActive && (
                      <span className="w-2 h-2 rounded-full bg-orange-500 shadow-xs" title="Active" />
                    )}
                  </div>
                </div>

                <p className="text-[10px] text-stone-500 leading-tight mb-2 line-clamp-2">
                  {prof.desc}
                </p>

                <div className="flex items-center justify-between pt-1 border-t border-stone-100">
                  <span className="text-[9px] text-stone-400 font-medium">
                    Clara: {prof.companionMood}
                  </span>
                  {!isDefault && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleProfileSelect(prof.id, true);
                      }}
                      className="text-[9px] text-orange-600 hover:text-orange-700 hover:underline font-medium"
                    >
                      Set Default
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Auto Context Switching & Depth Controls */}
      <div className="p-3 bg-white/70 backdrop-blur-sm border border-stone-200/80 rounded-2xl flex flex-col gap-3 shadow-xs">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-orange-500" />
            <div>
              <span className="text-xs font-semibold text-stone-900">Context-Aware Auto Switch</span>
              <p className="text-[10px] text-stone-500">
                Infers Teacher for technical study, Professional for desktop tasks, and Supportive for distress.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => handleUpdateSliders({ auto_switch_enabled: !settings.auto_switch_enabled })}
            className={`w-9 h-5 rounded-full transition relative cursor-pointer ${
              settings.auto_switch_enabled ? 'bg-orange-500' : 'bg-stone-300'
            }`}
          >
            <div
              className={`w-3.5 h-3.5 rounded-full bg-white transition-all transform absolute top-[3px] ${
                settings.auto_switch_enabled ? 'translate-x-[18px]' : 'translate-x-[3px]'
              }`}
            />
          </button>
        </div>

        {/* Explanation Depth */}
        <div className="flex flex-col gap-1.5 pt-2 border-t border-stone-200/50">
          <label className="text-[11px] font-semibold text-stone-700">Explanation Depth</label>
          <div className="grid grid-cols-3 gap-1 p-1 bg-stone-100/80 rounded-xl border border-stone-200/70 text-xs">
            {(['concise', 'balanced', 'in_depth'] as const).map((depth) => (
              <button
                key={depth}
                type="button"
                onClick={() => handleUpdateSliders({ explanation_depth: depth })}
                className={`py-1 rounded-lg text-center font-medium capitalize transition cursor-pointer ${
                  settings.explanation_depth === depth
                    ? 'bg-white text-orange-600 font-semibold shadow-xs'
                    : 'text-stone-500 hover:text-stone-800'
                }`}
              >
                {depth.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Nuance Sliders: Humor, Sarcasm, Formality */}
      <div className="p-3 bg-white/70 backdrop-blur-sm border border-stone-200/80 rounded-2xl flex flex-col gap-3 shadow-xs">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-stone-500 flex items-center gap-1.5">
          <Sliders className="w-3.5 h-3.5" />
          <span>Style Nuance Sliders</span>
        </div>

        {/* Humor Slider */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-stone-700">Humour Intensity</span>
            <span className="font-semibold text-orange-600">{settings.humor_intensity}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={settings.humor_intensity}
            onChange={(e) => handleUpdateSliders({ humor_intensity: Number(e.target.value) })}
            className="w-full accent-orange-500 h-1.5 bg-stone-200 rounded-lg cursor-pointer"
          />
          <div className="flex justify-between text-[9px] text-stone-400">
            <span>Serious</span>
            <span>Balanced</span>
            <span>Very Funny</span>
          </div>
        </div>

        {/* Sarcasm Slider */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-stone-700">Sarcasm & Banter</span>
            <span className="font-semibold text-orange-600">{settings.sarcasm_intensity}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={settings.sarcasm_intensity}
            onChange={(e) => handleUpdateSliders({ sarcasm_intensity: Number(e.target.value) })}
            className="w-full accent-orange-500 h-1.5 bg-stone-200 rounded-lg cursor-pointer"
          />
          <div className="flex justify-between text-[9px] text-stone-400">
            <span>Earnest (0%)</span>
            <span>Dry Wit (50%)</span>
            <span>Sharp Banter (100%)</span>
          </div>
        </div>

        {/* Formality Slider */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-stone-700">Formality Level</span>
            <span className="font-semibold text-orange-600">{settings.formality}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={settings.formality}
            onChange={(e) => handleUpdateSliders({ formality: Number(e.target.value) })}
            className="w-full accent-orange-500 h-1.5 bg-stone-200 rounded-lg cursor-pointer"
          />
          <div className="flex justify-between text-[9px] text-stone-400">
            <span>Casual</span>
            <span>Neutral</span>
            <span>Polished / Formal</span>
          </div>
        </div>

        {/* Proactivity Slider */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-stone-700">Proactive Conversation Frequency</span>
            <span className="font-semibold text-orange-600">{settings.proactivity}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={settings.proactivity}
            onChange={(e) => handleUpdateSliders({ proactivity: Number(e.target.value) })}
            className="w-full accent-orange-500 h-1.5 bg-stone-200 rounded-lg cursor-pointer"
          />
          <div className="flex justify-between text-[9px] text-stone-400">
            <span>Reactive Only (0%)</span>
            <span>Balanced (30%)</span>
            <span>Frequent (100%)</span>
          </div>
        </div>
      </div>

      {/* Safety & Sandbox Boundaries Notice */}
      <div className="p-2.5 bg-stone-50 border border-stone-200/60 rounded-xl flex items-start gap-2 text-stone-500 text-[10px] leading-relaxed">
        <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
        <span>
          <strong>Ethical Boundaries:</strong> AURA never mocks real human distress, never claims biological sentience, and strictly maintains sandbox security permissions across all social personas.
        </span>
      </div>
    </div>
  );
};
