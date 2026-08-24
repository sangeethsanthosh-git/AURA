import { Card } from "../components/ui/Card";
import { StatusPill } from "../components/ui/StatusPill";
import { useAuraRuntime } from "../state/AuraContext";

export function SettingsPage() {
  const { backend, providerStatus, voiceState } = useAuraRuntime();
  return (
    <div className="settings-grid">
      <Card title="System">
        <StatusPill label="Backend" state={backend} tone={backend === "READY" ? "good" : "bad"} />
        <p className="empty-state">Secrets and API keys are intentionally hidden from the renderer.</p>
      </Card>
      <Card title="AI Models">
        {Object.entries(providerStatus).map(([name, state]) => (
          <div className="key-row" key={name}>
            <span>{name}</span>
            <strong>{state}</strong>
          </div>
        ))}
      </Card>
      <Card title="Voice">
        <StatusPill label="Voice" state={voiceState} tone={voiceState === "RECORDING" ? "warn" : "neutral"} />
        <p className="empty-state">Voice profile selection needs a backend profile API before it becomes editable.</p>
      </Card>
      <Card title="Privacy">
        <div className="key-row"><span>Microphone</span><strong>On demand</strong></div>
        <div className="key-row"><span>Screen Vision</span><strong>On demand</strong></div>
        <div className="key-row"><span>Computer Control</span><strong>Confirmed actions</strong></div>
      </Card>
    </div>
  );
}
