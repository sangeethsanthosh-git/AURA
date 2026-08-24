import { AuraOrb } from "../components/AuraOrb";
import { ChatInput } from "../components/chat/ChatInput";
import { Button } from "../components/ui/Button";
import { useAuraRuntime } from "../state/AuraContext";
import { WidgetGrid } from "../widgets/WidgetGrid";

export function HomePage({ onOpenChat }: { onOpenChat: () => void }) {
  const { backend } = useAuraRuntime();
  return (
    <div className="home-page">
      <section className="home-hero">
        <AuraOrb state={backend === "READY" ? "READY" : backend} />
        <div className="hero-actions">
          <Button variant="primary" onClick={onOpenChat}>Open Chat</Button>
          <Button onClick={() => window.dispatchEvent(new CustomEvent("aura-command-focus"))}>Quick Ask</Button>
        </div>
      </section>
      <ChatInput onSend={(message) => {
        onOpenChat();
        window.dispatchEvent(new CustomEvent("aura-send-message", { detail: message }));
      }} disabled={backend !== "READY"} />
      <WidgetGrid />
    </div>
  );
}
