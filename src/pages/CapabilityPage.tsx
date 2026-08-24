import { Card } from "../components/ui/Card";

export function CapabilityPage({ title, capability }: { title: string; capability: string }) {
  return (
    <div className="page-stack">
      <Card title={title}>
        <p className="empty-state">{capability}</p>
      </Card>
    </div>
  );
}
