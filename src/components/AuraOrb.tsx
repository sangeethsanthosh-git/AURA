import { BackendState } from "../services/auraApi";

export function AuraOrb({ state }: { state: BackendState | "THINKING" | "LISTENING" | "SPEAKING" | "IDLE" }) {
  return (
    <div className="aura-presence" data-state={state}>
      <div className="aura-orb" />
      <div>
        <p>AURA</p>
        <h1>{state === "READY" || state === "IDLE" ? "I am here." : "Staying with it."}</h1>
      </div>
    </div>
  );
}
