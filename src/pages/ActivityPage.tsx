import { Card } from "../components/ui/Card";
import { useAuraRuntime } from "../state/AuraContext";

export function ActivityPage() {
  const { activities } = useAuraRuntime();
  return (
    <div className="page-stack">
      <Card title="Activity">
        {activities.length === 0 && <p className="empty-state">No AURA activity has been recorded in this session.</p>}
        {activities.map((item, index) => (
          <div className="list-item" key={`${item.user_message}-${index}`}>
            <div>
              <strong>{item.intent}</strong>
              <p>{item.user_message}</p>
              <small>{item.execution_source} · {item.execution_time.toFixed(2)}s</small>
            </div>
            <span className="result-chip" data-ok={item.success}>{item.success ? "OK" : "Error"}</span>
          </div>
        ))}
      </Card>
    </div>
  );
}
