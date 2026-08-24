import { useAuraRuntime } from "../state/AuraContext";
import { StatusPill } from "../components/ui/StatusPill";
import { WidgetDefinition } from "./widgetTypes";

function StatusWidget() {
  const { backend, providerStatus } = useAuraRuntime();
  return (
    <div className="widget-stack">
      <StatusPill label="AURA" state={backend} tone={backend === "READY" ? "good" : "warn"} />
      {Object.entries(providerStatus).slice(0, 4).map(([name, state]) => (
        <div className="key-row" key={name}>
          <span>{name}</span>
          <strong>{state}</strong>
        </div>
      ))}
    </div>
  );
}

function MemoryWidget() {
  const { memories } = useAuraRuntime();
  return memories.length ? (
    <div className="memory-peek">
      <strong>{memories.length}</strong>
      <span>active local memories</span>
      <p>{memories[0].content}</p>
    </div>
  ) : (
    <p className="empty-state">No active memories exposed by the backend yet.</p>
  );
}

function ActivityWidget() {
  const { activities } = useAuraRuntime();
  return activities.length ? (
    <div className="compact-list">
      {activities.slice(0, 3).map((item, index) => (
        <div className="key-row" key={`${item.user_message}-${index}`}>
          <span>{item.intent}</span>
          <strong>{item.success ? "Done" : "Error"}</strong>
        </div>
      ))}
    </div>
  ) : (
    <p className="empty-state">Activity will appear after your first AURA request.</p>
  );
}

function UnavailableWidget({ label }: { label: string }) {
  return <p className="empty-state">{label} is not exposed as a dedicated backend capability yet.</p>;
}

export const widgetRegistry: WidgetDefinition[] = [
  { id: "status", title: "AURA Status", size: "wide", priority: 1, refreshPolicy: "event", dataSource: "providerStatus", render: () => <StatusWidget /> },
  { id: "memory", title: "Memory", size: "medium", priority: 2, refreshPolicy: "on-load", dataSource: "listMemories", render: () => <MemoryWidget /> },
  { id: "activity", title: "Recent Activity", size: "medium", priority: 3, refreshPolicy: "event", dataSource: "activities", render: () => <ActivityWidget /> },
  { id: "weather", title: "Weather", size: "small", priority: 4, refreshPolicy: "manual", dataSource: "chat-weather-intent", render: () => <UnavailableWidget label="Weather widget data" /> },
  { id: "tasks", title: "Tasks", size: "small", priority: 5, refreshPolicy: "manual", dataSource: "not-available", render: () => <UnavailableWidget label="Task storage" /> },
  { id: "vision", title: "Vision", size: "small", priority: 6, refreshPolicy: "manual", dataSource: "chat-screen-intent", render: () => <p className="empty-state">Vision runs on demand through chat. No continuous screen capture.</p> },
];
