import { BackendState } from "../services/auraApi";

interface AuraOrbProps {
  state?: BackendState | "THINKING" | "LISTENING" | "SPEAKING" | "IDLE";
  size?: number;
  interactive?: boolean;
}

export function AuraOrb({ state = "IDLE", size = 120, interactive = true }: AuraOrbProps) {
  return (
    <div
      className="aura-iridescent-container"
      data-state={state}
      style={{ width: size, height: size }}
      title={`AURA Assistant (${state})`}
    >
      <div className="aura-halo-glow" />
      <div className="aura-orb-sphere">
        <div className="orb-specular-highlight" />
        <div className="orb-inner-chroma" />
        <div className="orb-iridescent-rim" />
      </div>
      {interactive && (
        <div className="orb-pulse-ring" />
      )}
    </div>
  );
}
