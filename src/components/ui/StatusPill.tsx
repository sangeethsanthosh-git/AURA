export function StatusPill({ label, state, tone = "neutral" }: { label: string; state: string; tone?: "good" | "warn" | "bad" | "neutral" }) {
  return (
    <span className="status-pill" data-tone={tone}>
      <span aria-hidden="true" />
      {label}: {state}
    </span>
  );
}
