import { AuraResponse } from "../../services/auraApi";

export type ChatItem = {
  id: string;
  role: "user" | "aura" | "system";
  text: string;
  response?: AuraResponse;
};

export function ChatMessage({ item }: { item: ChatItem }) {
  return (
    <article className="chat-message" data-role={item.role}>
      <div className="message-body">
        <p>{item.text}</p>
        {item.response && (
          <footer>
            <span>{item.response.intent}</span>
            <span>{item.response.execution_source}</span>
            <span>{item.response.execution_time.toFixed(2)}s</span>
          </footer>
        )}
      </div>
    </article>
  );
}
