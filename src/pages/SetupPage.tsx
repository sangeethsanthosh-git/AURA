import { useEffect, useMemo, useState } from "react";
import { auraApi } from "../services/auraApi";
import { saveAppSettings } from "../state/appSettings";

type SetupApiKey = {
  id: string;
  provider: "groq" | "huggingface" | "nvidia";
  label: string;
  value: string;
  status: "ready" | "limited" | "empty";
};

type SystemInfo = {
  platform: string;
  arch: string;
  totalMemoryGb: number;
  cpuCount: number;
  hostname: string;
  electron: string;
};

type ModelCandidate = {
  id: string;
  name: string;
  minRam: number;
  role: string;
  command: string;
  badge: string;
};

const WIZARD_STEPS = [
  { id: "profile", label: "Profile" },
  { id: "runtime", label: "Runtime" },
  { id: "model", label: "Models" },
  { id: "keys", label: "API Keys" },
  { id: "guide", label: "Guide" },
] as const;

const MODEL_CANDIDATES: ModelCandidate[] = [
  { id: "gemma3:1b", name: "Gemma 3 1B", minRam: 4, role: "Fast chat and commands", command: "ollama pull gemma3:1b", badge: "Light" },
  { id: "llama3.2:3b", name: "Llama 3.2 3B", minRam: 6, role: "Balanced daily assistant", command: "ollama pull llama3.2:3b", badge: "Balanced" },
  { id: "qwen3:4b", name: "Qwen 3 4B", minRam: 8, role: "Coding and planning", command: "ollama pull qwen3:4b", badge: "Sharper" },
  { id: "gemma3:4b", name: "Gemma 3 4B", minRam: 12, role: "Stronger writing and reasoning", command: "ollama pull gemma3:4b", badge: "Smart" },
  { id: "llama3.1:8b", name: "Llama 3.1 8B", minRam: 16, role: "Heavier daily reasoning", command: "ollama pull llama3.1:8b", badge: "Strong" },
  { id: "qwen2.5:14b", name: "Qwen 2.5 14B", minRam: 24, role: "Advanced reasoning and code", command: "ollama pull qwen2.5:14b", badge: "Pro" },
  { id: "gpt-oss:20b", name: "gpt-oss 20B", minRam: 32, role: "High-capacity local model", command: "ollama pull gpt-oss:20b", badge: "Max" },
];

const GUIDE_ITEMS = [
  "Use Studio for chat and commands.",
  "Install Ollama first, then wait for the download to finish.",
  "Add cloud keys only if you want Groq, Hugging Face, or NVIDIA.",
  "You can edit name, wallpaper, voice, and location later in Settings.",
];

const LINK_ITEMS = [
  { label: "Install Ollama", href: "https://ollama.com/download", note: "Download the local model runtime." },
  { label: "Get Groq key", href: "https://console.groq.com/keys", note: "Create your Groq API key." },
  { label: "Get Hugging Face key", href: "https://huggingface.co/settings/tokens", note: "Create your Hugging Face token." },
  { label: "Get NVIDIA key", href: "https://build.nvidia.com/", note: "Create your NVIDIA API key." },
] as const;

export function SetupPage({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(0);
  const [profileName, setProfileName] = useState("");
  const [assistantName, setAssistantName] = useState("AURA");
  const [age, setAge] = useState("");
  const [dob, setDob] = useState("");
  const [weatherCity, setWeatherCity] = useState("Kochi");
  const [reminderEmail, setReminderEmail] = useState("");
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [ollamaStatus, setOllamaStatus] = useState<"idle" | "checking" | "ready" | "missing">("idle");
  const [ollamaMessage, setOllamaMessage] = useState("Install Ollama, wait until it finishes, then verify it here.");
  const [keys, setKeys] = useState<SetupApiKey[]>([
    { id: "groq-primary", provider: "groq", label: "Groq primary", value: "", status: "empty" },
    { id: "hf-primary", provider: "huggingface", label: "HuggingFace primary", value: "", status: "empty" },
    { id: "nvidia-primary", provider: "nvidia", label: "NVIDIA Nemotron", value: "", status: "empty" },
  ]);
  const [selectedModel, setSelectedModel] = useState("gemma3:1b");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const systemInfoPromise = window.aura?.systemInfo();
    if (!systemInfoPromise) {
      const fallback = { platform: "unknown", arch: "unknown", totalMemoryGb: 8, cpuCount: 4, hostname: "This PC", electron: "" };
      setSystemInfo(fallback);
      setSelectedModel(recommendModel(fallback.totalMemoryGb).id);
      return;
    }
    void systemInfoPromise
      .then((info) => {
        setSystemInfo(info);
        setSelectedModel(recommendModel(info.totalMemoryGb).id);
      })
      .catch(() => {
        const fallback = { platform: "unknown", arch: "unknown", totalMemoryGb: 8, cpuCount: 4, hostname: "This PC", electron: "" };
        setSystemInfo(fallback);
        setSelectedModel(recommendModel(fallback.totalMemoryGb).id);
      });
  }, []);

  const capableModels = useMemo(() => {
    const ram = systemInfo?.totalMemoryGb || 8;
    return MODEL_CANDIDATES.filter((model) => model.minRam <= ram);
  }, [systemInfo]);

  useEffect(() => {
    if (systemInfo) {
      const best = recommendModel(systemInfo.totalMemoryGb);
      if (capableModels.some((model) => model.id === best.id)) {
        setSelectedModel(best.id);
      }
    }
  }, [systemInfo, capableModels]);

  function updateKey(id: string, value: string) {
    setKeys((current) => current.map((key) => (key.id === id ? { ...key, value, status: value.trim() ? "ready" : "empty" } : key)));
  }

  async function checkOllamaRuntime() {
    setOllamaStatus("checking");
    setOllamaMessage("Checking local Ollama runtime...");
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);
      const response = await fetch("http://127.0.0.1:11434/api/tags", { signal: controller.signal });
      clearTimeout(timeout);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      setOllamaStatus("ready");
      setOllamaMessage("Ollama is running. You can now pull a model.");
    } catch {
      setOllamaStatus("missing");
      setOllamaMessage("Ollama is not ready yet. Install it, wait for the download to finish, then check again.");
    }
  }

  async function installOllama() {
    setOllamaStatus("checking");
    setOllamaMessage("Starting Ollama installer in the background...");
    try {
      const result = await window.aura?.settings.installOllama?.();
      if (result?.ok) {
        setOllamaMessage(result.message || "Ollama installer started. Wait for it to finish, then verify again.");
        return;
      }
      throw new Error(result?.message || "Installer request failed");
    } catch {
      setOllamaStatus("missing");
      setOllamaMessage("Could not start the installer from the app. Open the Ollama download page manually.");
    }
  }

  async function finishSetup() {
    setSaving(true);
    saveAppSettings({
      profileName: profileName.trim() || "User",
      assistantName: assistantName.trim() || "AURA",
      age,
      dob,
      weatherCity: weatherCity.trim() || "Kochi",
      reminderEmail,
      defaultModel: selectedModel,
      setupComplete: true,
    });
    await auraApi.saveProviderKeys(keys.map((key) => ({ ...key, status: key.value.trim() ? "ready" : "empty" })));
    setSaving(false);
    onComplete();
  }

  function goNext() {
    if (step < WIZARD_STEPS.length - 1) {
      setStep((current) => current + 1);
      return;
    }
    void finishSetup();
  }

  function goBack() {
    setStep((current) => Math.max(0, current - 1));
  }

  const selected = MODEL_CANDIDATES.find((model) => model.id === selectedModel) || MODEL_CANDIDATES[0];

  return (
    <main className="setup-shell" aria-label="AURA first run setup">
      <section className="setup-window">
        <header className="setup-titlebar">
          <div className="setup-app-id">
            <span>A</span>
            <strong>Setting up {assistantName || "AURA"}</strong>
          </div>
          <button type="button" onClick={finishSetup}>Skip</button>
        </header>

        <div className="setup-body">
          <aside className="setup-progress">
            <div>
              <h1>Preparing your assistant</h1>
              <p>Finish one step at a time. The app opens only after you complete the setup flow.</p>
            </div>
            <ol>
              {WIZARD_STEPS.map((item, index) => (
                <li key={item.id} className={index === step ? "active" : index < step ? "done" : ""}>
                  <span>{index + 1}</span>
                  {item.label}
                </li>
              ))}
            </ol>
          </aside>

          <section className="setup-panel">
            {step === 0 && (
              <section className="setup-step">
                <div className="setup-step-header">
                  <h2>Profile</h2>
                  <p>Set the identity and defaults for this install.</p>
                </div>

                <div className="setup-grid">
                  <label>
                    <span>Your name</span>
                    <input value={profileName} onChange={(event) => setProfileName(event.target.value)} placeholder="Enter your name" />
                  </label>
                  <label>
                    <span>Assistant name</span>
                    <input value={assistantName} onChange={(event) => setAssistantName(event.target.value)} placeholder="AURA" />
                  </label>
                  <label>
                    <span>Age</span>
                    <input value={age} onChange={(event) => setAge(event.target.value)} inputMode="numeric" placeholder="Optional" />
                  </label>
                  <label>
                    <span>Date of birth</span>
                    <input type="date" value={dob} onChange={(event) => setDob(event.target.value)} />
                  </label>
                  <label>
                    <span>Weather place</span>
                    <input value={weatherCity} onChange={(event) => setWeatherCity(event.target.value)} placeholder="Kochi" />
                  </label>
                  <label>
                    <span>Reminder email</span>
                    <input value={reminderEmail} onChange={(event) => setReminderEmail(event.target.value)} placeholder="name@example.com" />
                  </label>
                </div>

                <div className="setup-system-card">
                  <span>Hardware profile</span>
                  <strong>{systemInfo ? `${systemInfo.totalMemoryGb} GB RAM | ${systemInfo.cpuCount} CPU threads` : "Scanning..."}</strong>
                  <small>{systemInfo ? `${systemInfo.hostname} | ${systemInfo.platform} ${systemInfo.arch}` : "Checking this computer"}</small>
                </div>
              </section>
            )}

            {step === 1 && (
              <section className="setup-step">
                <div className="setup-step-header">
                  <h2>Runtime</h2>
                  <p>Install Ollama first, wait for it to finish, then verify it here.</p>
                </div>

                <div className="setup-link-grid">
                  <a className="setup-link-card" href="https://ollama.com/download" target="_blank" rel="noreferrer">
                    <span className="setup-link-icon">D</span>
                    <strong>Download Ollama</strong>
                    <small>Open the official download page.</small>
                  </a>
                  <button className="setup-link-card" type="button" onClick={installOllama}>
                    <span className="setup-link-icon">I</span>
                    <strong>Install Ollama</strong>
                    <small>Run the official installer in the background.</small>
                  </button>
                  <button className="setup-link-card" type="button" onClick={checkOllamaRuntime}>
                    <span className="setup-link-icon">?</span>
                    <strong>Verify Ollama</strong>
                    <small>{ollamaStatus === "ready" ? "Runtime is ready." : "Click after install completes."}</small>
                  </button>
                </div>

                <div className="setup-system-card">
                  <span>Ollama status</span>
                  <strong>{ollamaStatus === "ready" ? "Ready" : ollamaStatus === "missing" ? "Not detected" : ollamaStatus === "checking" ? "Checking..." : "Waiting"}</strong>
                  <small>{ollamaMessage}</small>
                </div>

                <p className="setup-help-note">
                  Ollama is the local runtime. Once it is installed, the next step will suggest models that fit this machine.
                </p>
              </section>
            )}

            {step === 2 && (
              <section className="setup-step">
                <div className="setup-step-header">
                  <h2>Models</h2>
                  <p>Only models that fit your machine are shown.</p>
                </div>

                <div className="setup-model-list">
                  {capableModels.map((model) => (
                    <button key={model.id} type="button" className={selectedModel === model.id ? "active" : ""} onClick={() => setSelectedModel(model.id)}>
                      <span className="setup-model-badge">{model.badge}</span>
                      <strong>{model.name}</strong>
                      <small>{model.role}</small>
                    </button>
                  ))}
                </div>

                <p className="setup-help-note">
                  Ollama is required for local models. After it finishes installing, run: <code>{selected.command}</code>
                </p>
              </section>
            )}

            {step === 3 && (
              <section className="setup-step">
                <div className="setup-step-header">
                  <h2>API Keys</h2>
                  <p>Paste keys now or open each provider in a new tab.</p>
                </div>

                <div className="setup-link-grid">
                  {LINK_ITEMS.slice(1).map((item) => (
                    <a key={item.label} className="setup-link-card" href={item.href} target="_blank" rel="noreferrer">
                      <span className="setup-link-icon">↗</span>
                      <strong>{item.label}</strong>
                      <small>{item.note}</small>
                    </a>
                  ))}
                </div>

                <div className="setup-card">
                  <div className="setup-section-title">
                    <h3>Optional stored keys</h3>
                    <span>Saved locally on this computer</span>
                  </div>
                  <div className="setup-key-list">
                    {keys.map((key) => (
                      <label key={key.id}>
                        <span>{key.label}</span>
                        <input type="password" value={key.value} onChange={(event) => updateKey(key.id, event.target.value)} placeholder={`Paste ${key.provider} key`} />
                      </label>
                    ))}
                  </div>
                </div>
              </section>
            )}

            {step === 4 && (
              <section className="setup-step">
                <div className="setup-step-header">
                  <h2>Guide</h2>
                  <p>Quick links and the first things to do after install.</p>
                </div>

                <div className="setup-link-grid">
                  <a className="setup-link-card" href="https://ollama.com/download" target="_blank" rel="noreferrer">
                    <span className="setup-link-icon">O</span>
                    <strong>Ollama download</strong>
                    <small>Local model runtime</small>
                  </a>
                  <a className="setup-link-card" href="https://console.groq.com/keys" target="_blank" rel="noreferrer">
                    <span className="setup-link-icon">G</span>
                    <strong>Groq API</strong>
                    <small>Create your Groq key</small>
                  </a>
                  <a className="setup-link-card" href="https://huggingface.co/settings/tokens" target="_blank" rel="noreferrer">
                    <span className="setup-link-icon">H</span>
                    <strong>Hugging Face</strong>
                    <small>Create your token</small>
                  </a>
                  <a className="setup-link-card" href="https://build.nvidia.com/" target="_blank" rel="noreferrer">
                    <span className="setup-link-icon">N</span>
                    <strong>NVIDIA</strong>
                    <small>Create your API key</small>
                  </a>
                </div>

                <div className="setup-guide">
                  {GUIDE_ITEMS.map((item) => <span key={item}>{item}</span>)}
                </div>

                <p className="setup-help-note">
                  If your machine has more RAM, this setup will surface larger models too, not just 4B-class options.
                </p>
              </section>
            )}

            <footer className="setup-actions">
              <button type="button" onClick={goBack} disabled={step === 0}>Back</button>
              <button type="button" className="primary" disabled={saving} onClick={goNext}>
                {saving ? "Saving..." : step === WIZARD_STEPS.length - 1 ? "Start AURA" : "Next"}
              </button>
            </footer>
          </section>
        </div>
      </section>
    </main>
  );
}

function recommendModel(totalMemoryGb: number) {
  return [...MODEL_CANDIDATES].reverse().find((model) => model.minRam <= totalMemoryGb) || MODEL_CANDIDATES[0];
}
