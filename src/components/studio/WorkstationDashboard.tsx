import { WorkstationInspector } from "../widgets/WorkstationInspector";

interface WorkstationDashboardProps {
  title?: string;
  onTriggerPrompt?: (prompt: string) => void;
}

export function WorkstationDashboard({ title = "AURA Dashboard", onTriggerPrompt }: WorkstationDashboardProps) {
  return (
    <section className="workstation-dashboard-board" aria-label="AURA workstation dashboard">
      <header className="workstation-dashboard-header">
        <div>
          <span>Multi View Panel</span>
          <h1>{title}</h1>
        </div>
        <div className="workstation-dashboard-status">
          <span>Search</span>
          <span>Music</span>
          <span>Weather</span>
          <span>Schedule</span>
        </div>
      </header>
      <WorkstationInspector onTriggerPrompt={onTriggerPrompt} />
    </section>
  );
}
