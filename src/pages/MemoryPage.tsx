import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { auraApi } from "../services/auraApi";
import { useAuraRuntime } from "../state/AuraContext";

export function MemoryPage() {
  const { memories, refreshRuntime } = useAuraRuntime();
  return (
    <div className="page-stack">
      <Card title="Memory">
        {memories.length === 0 && <p className="empty-state">AURA has no active long-term memories to show.</p>}
        {memories.map((memory) => (
          <div className="list-item" key={memory.id || memory.content}>
            <div>
              <strong>{memory.category}</strong>
              <p>{memory.content}</p>
            </div>
            <Button onClick={async () => {
              await auraApi.forgetMemory(memory.content);
              await refreshRuntime();
            }}>Forget</Button>
          </div>
        ))}
      </Card>
    </div>
  );
}
