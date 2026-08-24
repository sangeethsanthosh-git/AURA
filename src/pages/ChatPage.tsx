import { useEffect, useState } from "react";
import { ChatInput } from "../components/chat/ChatInput";
import { ChatItem, ChatMessage } from "../components/chat/ChatMessage";
import { auraApi } from "../services/auraApi";
import { useAuraRuntime } from "../state/AuraContext";

export function ChatPage() {
  const { backend, refreshRuntime } = useAuraRuntime();
  const [items, setItems] = useState<ChatItem[]>([
    { id: "hello", role: "aura", text: "I am here. Ask me something local, practical, or a little strange." },
  ]);
  const [busy, setBusy] = useState(false);

  async function send(message: string) {
    setItems((current) => [...current, { id: crypto.randomUUID(), role: "user", text: message }]);
    setBusy(true);
    try {
      const response = await auraApi.sendMessage(message);
      setItems((current) => [...current, { id: crypto.randomUUID(), role: "aura", text: response.text, response }]);
      await refreshRuntime();
    } catch (error) {
      setItems((current) => [...current, { id: crypto.randomUUID(), role: "system", text: error instanceof Error ? error.message : "AURA backend is offline." }]);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    const handler = (event: Event) => {
      const message = (event as CustomEvent<string>).detail;
      if (message) {
        void send(message);
      }
    };
    window.addEventListener("aura-send-message", handler);
    return () => window.removeEventListener("aura-send-message", handler);
  }, []);

  return (
    <div className="chat-page">
      <section className="chat-stream" aria-live="polite">
        {items.map((item) => <ChatMessage key={item.id} item={item} />)}
        {busy && <ChatMessage item={{ id: "thinking", role: "aura", text: "Thinking..." }} />}
      </section>
      <ChatInput disabled={busy || backend !== "READY"} onSend={send} />
    </div>
  );
}
