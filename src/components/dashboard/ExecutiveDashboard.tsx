import { WorkstationDashboard } from "../studio/WorkstationDashboard";

interface ExecutiveDashboardProps {
  onTriggerPrompt?: (prompt: string) => void;
}

export function ExecutiveDashboard({ onTriggerPrompt }: ExecutiveDashboardProps) {
  return (
    <div className="executive-dashboard-container executive-dashboard-container--cards" aria-label="Executive Productivity Dashboard">
      <WorkstationDashboard title="AURA Dashboard" onTriggerPrompt={onTriggerPrompt} />
    </div>
  );
}
