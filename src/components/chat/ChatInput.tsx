import { FormEvent, useState } from "react";
import { Button } from "../ui/Button";

export function ChatInput({ disabled, onSend }: { disabled?: boolean; onSend: (message: string) => void }) {
  const [message, setMessage] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    const clean = message.trim();
    if (!clean) {
      return;
    }
    onSend(clean);
    setMessage("");
  }

  return (
    <form className="chat-input" onSubmit={submit}>
      <input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Ask AURA anything..." disabled={disabled} />
      <Button type="button" variant="ghost" disabled title="Attachments are not exposed by the backend yet.">+</Button>
      <Button type="button" variant="ghost" title="Voice input is available on the Voice page.">Mic</Button>
      <Button type="submit" variant="primary" disabled={disabled || !message.trim()}>↑</Button>
    </form>
  );
}
