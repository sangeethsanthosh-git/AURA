import { useEffect, useMemo, useState } from "react";
import { useAuraRuntime } from "../state/AuraContext";
import { auraApi } from "../services/auraApi";
import { readAppSettings, saveAppSettings } from "../state/appSettings";

type SettingsTab = "profile" | "ai" | "voice" | "privacy" | "integrations" | "appearance" | "advanced";

const SETTINGS_TABS: Array<{ id: SettingsTab; label: string; group: string; icon: string }> = [
  { id: "profile", label: "Profile", group: "Customize", icon: "P" },
  { id: "ai", label: "AI Engines", group: "Customize", icon: "AI" },
  { id: "voice", label: "Voice", group: "Customize", icon: "V" },
  { id: "privacy", label: "Privacy", group: "Control", icon: "PR" },
  { id: "integrations", label: "Integrations", group: "Control", icon: "IN" },
  { id: "appearance", label: "Appearance", group: "Tools", icon: "UI" },
  { id: "advanced", label: "Advanced", group: "Tools", icon: "AD" },
];

const MODEL_OPTIONS = ["Auto Router", "NVIDIA Nemotron", "gemma3:1b", "gemma3:4b", "llama3.2:3b", "qwen3:4b"];
const VOICE_OPTIONS = ["Piper LJSpeech High", "Piper English Fast", "Indic F5 Malayalam", "Indic Parler Tamil"];
const VOICE_TONE_OPTIONS = ["Neutral", "Male", "Female", "Boyfriend", "Girlfriend", "Soft male", "Soft female"];
const NEWS_OPTIONS = ["Top headlines", "Technology", "World", "India", "Science", "Business"];

type SystemInfo = {
  platform: string;
  arch: string;
  totalMemoryGb: number;
  cpuCount: number;
  hostname: string;
  electron: string;
};

const MODEL_CANDIDATES = [
  { id: "gemma3:1b", name: "Gemma 3 1B", minRam: 4, note: "Fast local chat and commands." },
  { id: "llama3.2:3b", name: "Llama 3.2 3B", minRam: 8, note: "Balanced daily assistant." },
  { id: "qwen3:4b", name: "Qwen 3 4B", minRam: 12, note: "Good for coding and planning." },
  { id: "gemma3:4b", name: "Gemma 3 4B", minRam: 16, note: "Best for bigger responses." },
] as const;

type ApiKeyProvider = "groq" | "huggingface" | "nvidia";

type ApiKeyDraft = {
  id: string;
  provider: ApiKeyProvider;
  label: string;
  value: string;
  status: "ready" | "limited" | "empty";
};

const PROVIDER_LABELS: Record<ApiKeyProvider, string> = {
  groq: "Groq",
  huggingface: "HuggingFace",
  nvidia: "NVIDIA NIM",
};

const DEFAULT_API_KEYS: ApiKeyDraft[] = [
  { id: "groq-primary", provider: "groq", label: "Groq primary", value: "", status: "ready" },
  { id: "hf-primary", provider: "huggingface", label: "HuggingFace primary", value: "", status: "ready" },
  { id: "nvidia-primary", provider: "nvidia", label: "NVIDIA Nemotron", value: "", status: "ready" },
];

export function SettingsPage() {
  const { backend, providerStatus, memories, activities, voiceState, refreshRuntime } = useAuraRuntime();
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  const [assistantEnabled, setAssistantEnabled] = useState(true);
  const [localControl, setLocalControl] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [newsImages, setNewsImages] = useState(true);
  const [memoryRecall, setMemoryRecall] = useState(true);
  const initialSettings = readAppSettings();
  const [profileName, setProfileName] = useState(initialSettings.profileName);
  const [assistantName, setAssistantName] = useState(initialSettings.assistantName || "AURA");
  const [accountEmail, setAccountEmail] = useState(initialSettings.accountEmail);
  const [reminderEmail, setReminderEmail] = useState(initialSettings.reminderEmail);
  const [reminderPhone, setReminderPhone] = useState(initialSettings.reminderPhone);
  const [weatherCity, setWeatherCity] = useState(initialSettings.weatherCity);
  const [avatarImage, setAvatarImage] = useState(initialSettings.avatarImage);
  const [backgroundImage, setBackgroundImage] = useState(initialSettings.backgroundImage);
  const [themeMode, setThemeMode] = useState(initialSettings.themeMode || "system");
  const [model, setModel] = useState(MODEL_OPTIONS[0]);
  const [voice, setVoice] = useState(VOICE_OPTIONS[0]);
  const [voiceTone, setVoiceTone] = useState(initialSettings.voiceTone || VOICE_TONE_OPTIONS[0]);
  const [newsCategory, setNewsCategory] = useState(NEWS_OPTIONS[0]);
  const [apiKeys, setApiKeys] = useState<ApiKeyDraft[]>(() => readApiKeyDrafts());
  const [saved, setSaved] = useState(false);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const displayName = profileName.trim() || "User";
  const profileInitials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || "")
    .join("") || "U";

  const providerRows = useMemo(() => Object.entries(providerStatus), [providerStatus]);

  useEffect(() => {
    void auraApi.loadProviderKeys().then((loaded) => {
      if (loaded.length) {
        setApiKeys(loaded.map((item) => ({ ...item })));
      }
    });
  }, []);

  useEffect(() => {
    const systemInfoPromise = window.aura?.systemInfo();
    if (!systemInfoPromise) {
      setSystemInfo(null);
      return;
    }
    void systemInfoPromise.then(setSystemInfo).catch(() => setSystemInfo(null));
  }, []);

  const capableModels = useMemo(() => {
    const ram = systemInfo?.totalMemoryGb || 8;
    return MODEL_CANDIDATES.filter((model) => model.minRam <= ram);
  }, [systemInfo]);

  async function saveChanges() {
    localStorage.setItem("aura:api-key-drafts", JSON.stringify(apiKeys.map((key) => ({ ...key, value: "" }))));
    localStorage.setItem("aura.companion.reminder-prefs", JSON.stringify({ email: reminderEmail, phone: reminderPhone }));
    saveAppSettings({
      profileName,
      assistantName,
      accountEmail,
      defaultModel: model,
      weatherCity,
      reminderEmail,
      reminderPhone,
      avatarImage,
      backgroundImage,
      themeMode,
      voiceTone,
    });
    await auraApi.saveProviderKeys(apiKeys);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1800);
  }

  function addProviderKey(provider: ApiKeyProvider) {
    setApiKeys((current) => [
      ...current,
      {
        id: `${provider}-${Date.now()}`,
        provider,
        label: `${PROVIDER_LABELS[provider]} fallback ${current.filter((key) => key.provider === provider).length + 1}`,
        value: "",
        status: "empty",
      },
    ]);
  }

  function updateApiKey(id: string, patch: Partial<ApiKeyDraft>) {
    setApiKeys((current) => current.map((key) => (key.id === id ? { ...key, ...patch } : key)));
  }

  function removeApiKey(id: string) {
    setApiKeys((current) => current.filter((key) => key.id !== id));
  }

  function resetSetup() {
    saveAppSettings({ setupComplete: false });
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1800);
  }

  async function handleImageUpload(file: File | null, setter: (value: string) => void) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setter(typeof reader.result === "string" ? reader.result : "");
    reader.readAsDataURL(file);
  }

  return (
    <div className="settings-desktop-shell" aria-label="AURA Settings">
      <aside className="settings-desktop-sidebar">
        <div className="settings-brand-row">
          <span className="settings-brand-mark">A</span>
          <strong>AURA</strong>
        </div>

        {["Customize", "Control", "Tools"].map((group) => (
          <div key={group} className="settings-nav-group">
            <span>{group}</span>
            {SETTINGS_TABS.filter((tab) => tab.group === group).map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={activeTab === tab.id ? "active" : ""}
                onClick={() => setActiveTab(tab.id)}
              >
                <i>{tab.icon}</i>
                {tab.label}
              </button>
            ))}
          </div>
        ))}
      </aside>

      <main className="settings-desktop-main">
        <header className="settings-top-profile">
          <div className="settings-user-chip">
            <span>{profileInitials}</span>
            <div>
              <strong>{displayName}</strong>
              <small>Last edited just now</small>
            </div>
          </div>
        </header>

        <section className="settings-content-grid">
          <aside className="settings-section-index">
            <h1>Settings</h1>
            <button type="button" className={activeTab === "profile" ? "active" : ""} onClick={() => setActiveTab("profile")}>Account</button>
            <button type="button" className={activeTab === "ai" ? "active" : ""} onClick={() => setActiveTab("ai")}>Model router</button>
            <button type="button" className={activeTab === "voice" ? "active" : ""} onClick={() => setActiveTab("voice")}>Voice companion</button>
            <button type="button" className={activeTab === "privacy" ? "active" : ""} onClick={() => setActiveTab("privacy")}>Permissions</button>
            <button type="button" className={activeTab === "integrations" ? "active" : ""} onClick={() => setActiveTab("integrations")}>News, weather, media</button>
            <button type="button" className={activeTab === "appearance" ? "active" : ""} onClick={() => setActiveTab("appearance")}>Interface</button>
          </aside>

          <div className="settings-primary-panel">
            <div className="settings-panel-heading">
              <h2>{titleForTab(activeTab)}</h2>
              <p>{descriptionForTab(activeTab)}</p>
            </div>

            <div className="settings-card-stack">
              {(activeTab === "profile" || activeTab === "appearance") && (
                <section className="settings-edit-card">
                  <h3>Edit details</h3>
                  <label>
                    <span>Assistant name</span>
                    <input value={assistantName} onChange={(event) => setAssistantName(event.target.value)} placeholder="AURA" />
                  </label>
                  <label>
                    <span>Your name</span>
                    <input value={profileName} onChange={(event) => setProfileName(event.target.value)} />
                  </label>
                  <label>
                    <span>Account email</span>
                    <input value={accountEmail} onChange={(event) => setAccountEmail(event.target.value)} placeholder="name@example.com" />
                  </label>
                  <label>
                    <span>Timezone</span>
                    <input value={Intl.DateTimeFormat().resolvedOptions().timeZone} readOnly />
                  </label>
                  <label>
                    <span>Locale</span>
                    <select defaultValue="English (US)">
                      <option>English (US)</option>
                      <option>English (India)</option>
                      <option>Malayalam</option>
                      <option>Hindi</option>
                      <option>Tamil</option>
                    </select>
                  </label>
                  <label>
                    <span>Theme</span>
                    <select value={themeMode} onChange={(event) => setThemeMode(event.target.value as "system" | "light" | "dark")}>
                      <option value="system">System</option>
                      <option value="light">Light</option>
                      <option value="dark">Dark</option>
                    </select>
                  </label>
                  <label>
                    <span>Avatar photo</span>
                    <input type="file" accept="image/*" onChange={(event) => void handleImageUpload(event.target.files?.[0] || null, setAvatarImage)} />
                  </label>
                  <label>
                    <span>App wallpaper</span>
                    <input type="file" accept="image/*,image/gif" onChange={(event) => void handleImageUpload(event.target.files?.[0] || null, setBackgroundImage)} />
                  </label>
                </section>
              )}

              {(activeTab === "ai" || activeTab === "advanced") && (
                <section className="settings-edit-card">
                  <h3>AI routing</h3>
                  <SettingSelect label="Default Ollama model" value={model} onChange={setModel} options={capableModels.map((item) => item.id)} />
                  <div className="settings-model-hints">
                    {capableModels.map((item) => (
                      <button key={item.id} type="button" className={model === item.id ? "active" : ""} onClick={() => setModel(item.id)}>
                        <strong>{item.name}</strong>
                        <small>{item.note}</small>
                      </button>
                    ))}
                  </div>
                  <SettingToggle title="Assistant everywhere" description="Show the AURA companion toggle across workspace pages." checked={assistantEnabled} onChange={setAssistantEnabled} />
                  <SettingToggle title="Use memory before routing" description={`${memories.length} memory records available for context.`} checked={memoryRecall} onChange={setMemoryRecall} tone="green" />
                  <SettingToggle title="Local control confirmation" description="Ask before opening apps, files, or sending media controls." checked={localControl} onChange={setLocalControl} />
                  <p className="settings-help-note">Ollama is required for local models. AURA only shows models this computer can realistically run.</p>
                </section>
              )}

              {(activeTab === "ai" || activeTab === "integrations" || activeTab === "advanced") && (
                <section className="settings-edit-card settings-api-key-card">
                  <div className="settings-inline-heading">
                    <h3>Provider API keys</h3>
                    <span>Keys stay local. Open-source users add their own during setup.</span>
                  </div>

                  <div className="settings-provider-actions">
                    <button type="button" onClick={() => addProviderKey("groq")}>Add Groq key</button>
                    <button type="button" onClick={() => addProviderKey("huggingface")}>Add HuggingFace key</button>
                    <button type="button" onClick={() => addProviderKey("nvidia")}>Add NVIDIA key</button>
                  </div>

                  <div className="settings-api-key-list">
                    {apiKeys.map((key) => (
                      <div key={key.id} className={`settings-api-key-row status-${key.status}`}>
                        <select value={key.provider} onChange={(event) => updateApiKey(key.id, { provider: event.target.value as ApiKeyProvider })}>
                          <option value="groq">Groq</option>
                          <option value="huggingface">HuggingFace</option>
                          <option value="nvidia">NVIDIA NIM</option>
                        </select>
                        <input value={key.label} onChange={(event) => updateApiKey(key.id, { label: event.target.value })} placeholder="Key label" />
                        <input
                          type="password"
                          value={key.value}
                          onChange={(event) => updateApiKey(key.id, { value: event.target.value, status: event.target.value ? "ready" : "empty" })}
                          placeholder="Paste API key locally"
                        />
                        <select value={key.status} onChange={(event) => updateApiKey(key.id, { status: event.target.value as ApiKeyDraft["status"] })}>
                          <option value="ready">Ready</option>
                          <option value="limited">Token limited</option>
                          <option value="empty">Empty</option>
                        </select>
                        <button type="button" onClick={() => removeApiKey(key.id)} title="Remove key">Remove</button>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {(activeTab === "voice" || activeTab === "advanced") && (
                <section className="settings-edit-card">
                  <h3>Voice companion</h3>
                  {activeTab === "advanced" && (
                    <>
                      <h3>Setup and install</h3>
                      <p className="settings-help-note">Restart the first-run setup if you want to re-enter name, age, DOB, keys, or model preferences.</p>
                      <button type="button" className="settings-secondary-button" onClick={resetSetup}>Run setup again</button>
                    </>
                  )}
                  <SettingSelect label="Open-source TTS voice" value={voice} onChange={setVoice} options={VOICE_OPTIONS} />
                  <SettingSelect label="Voice tone" value={voiceTone} onChange={setVoiceTone} options={VOICE_TONE_OPTIONS} />
                  <SettingToggle title="Piper TTS enabled" description={`Voice engine is ${voiceState.toLowerCase()}.`} checked={voiceEnabled} onChange={setVoiceEnabled} tone="green" />
                  <SettingToggle title="Speak assistant replies" description="Read compatible answers aloud without speaking emoji or symbols." checked={autoSpeak} onChange={setAutoSpeak} />
                  <SettingToggle title="Voice input" description="Enable talk mode for live conversation." checked={voiceEnabled} onChange={setVoiceEnabled} tone="green" />
                </section>
              )}

              {(activeTab === "privacy" || activeTab === "advanced") && (
                <section className="settings-edit-card">
                  <h3>Privacy and permissions</h3>
                  <SettingToggle title="Microphone on demand" description="Voice capture starts only from a button or command." checked={voiceEnabled} onChange={setVoiceEnabled} tone="green" />
                  <SettingToggle title="Store personal memory" description="Save preferences and project facts only when memory is enabled." checked={memoryRecall} onChange={setMemoryRecall} />
                  <label>
                    <span>Reminder email</span>
                    <input value={reminderEmail} onChange={(event) => setReminderEmail(event.target.value)} placeholder="name@example.com" />
                  </label>
                  <label>
                    <span>Reminder phone / gateway</span>
                    <input value={reminderPhone} onChange={(event) => setReminderPhone(event.target.value)} placeholder="+15551234567 or SMS gateway" />
                  </label>
                </section>
              )}

              {(activeTab === "integrations" || activeTab === "advanced") && (
                <section className="settings-edit-card">
                  <h3>Live widgets</h3>
                  <label>
                    <span>Weather place</span>
                    <input value={weatherCity} onChange={(event) => setWeatherCity(event.target.value)} placeholder="Search city" />
                  </label>
                  <SettingSelect label="News category" value={newsCategory} onChange={setNewsCategory} options={NEWS_OPTIONS} />
                  <SettingToggle title="News images" description="Show story photos in Editorial Insights and news cards." checked={newsImages} onChange={setNewsImages} tone="green" />
                  <p className="settings-help-note">
                    Capable models on this machine: {capableModels.map((item) => item.name).join(", ") || "none"}
                  </p>
                </section>
              )}
            </div>
          </div>

          <aside className="settings-checklist-panel">
            

            <button type="button" className="settings-save-button" onClick={saveChanges}>
              {saved ? "Saved" : "Save changes"}
            </button>
          </aside>
        </section>
      </main>
    </div>
  );
}

function SettingToggle({ title, description, checked, onChange, tone = "neutral" }: {
  title: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  tone?: "neutral" | "green";
}) {
  return (
    <button type="button" className={`settings-toggle-row ${checked ? "checked" : ""} tone-${tone}`} onClick={() => onChange(!checked)}>
      <span>
        <strong>{title}</strong>
        <small>{description}</small>
      </span>
      <i aria-hidden="true" />
    </button>
  );
}

function SettingSelect({ label, value, onChange, options }: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
}) {
  return (
    <label>
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => <option key={option}>{option}</option>)}
      </select>
    </label>
  );
}

function CheckRow({ label, detail, checked }: { label: string; detail?: string; checked: boolean }) {
  return (
    <div className="settings-check-row">
      <span>
        <strong>{label}</strong>
        {detail && <small>{detail}</small>}
      </span>
      <i className={checked ? "checked" : ""} />
    </div>
  );
}

function titleForTab(tab: SettingsTab) {
  const titles: Record<SettingsTab, string> = {
    profile: "Account settings",
    ai: "AI engine settings",
    voice: "Voice settings",
    privacy: "Privacy settings",
    integrations: "Integration settings",
    appearance: "Interface settings",
    advanced: "Advanced controls",
  };
  return titles[tab];
}

function descriptionForTab(tab: SettingsTab) {
  const descriptions: Record<SettingsTab, string> = {
    profile: "Manage identity, locale, and the profile details AURA uses in the workspace.",
    ai: "Choose routing defaults for Ollama, memory recall, and local assistant behavior.",
    voice: "Control open-source TTS voices and spoken assistant responses.",
    privacy: "Decide what AURA can read, remember, and control on this desktop.",
    integrations: "Tune weather, news, media, and external data widgets.",
    appearance: "Adjust the app interface, theme, and user-facing defaults.",
    advanced: "Review project capability switches and system-level options.",
  };
  return descriptions[tab];
}

function readApiKeyDrafts() {
  if (typeof window === "undefined") {
    return DEFAULT_API_KEYS;
  }
  try {
    const saved = window.localStorage.getItem("aura:api-key-drafts");
    if (!saved) return DEFAULT_API_KEYS;
    const parsed = JSON.parse(saved);
    if (!Array.isArray(parsed)) return DEFAULT_API_KEYS;
    return parsed.map((item, index) => ({
      id: String(item.id || `key-${index}`),
      provider: item.provider === "huggingface" || item.provider === "nvidia" ? item.provider : "groq",
      label: String(item.label || "API key"),
      value: "",
      status: item.status === "limited" || item.status === "empty" ? item.status : "ready",
    })) as ApiKeyDraft[];
  } catch {
    return DEFAULT_API_KEYS;
  }
}
