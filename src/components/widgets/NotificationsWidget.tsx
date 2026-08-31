import { useMemo, useState } from "react";

type NotificationItem = {
  id: string;
  title: string;
  body: string;
  time: string;
  tone: "system" | "memory" | "calendar";
};

const DEFAULT_NOTIFICATIONS: NotificationItem[] = [
  {
    id: "n1",
    title: "AURA is ready",
    body: "Local routing, media controls, and widgets are available.",
    time: "Now",
    tone: "system",
  },
  {
    id: "n2",
    title: "Calendar focus block",
    body: "Product design review is pinned in today's schedule.",
    time: "Today",
    tone: "calendar",
  },
  {
    id: "n3",
    title: "Memory reminder",
    body: "Use Memory to save project pipeline decisions.",
    time: "Recent",
    tone: "memory",
  },
];

export function NotificationsWidget() {
  const [permission, setPermission] = useState(() => {
    if (typeof window === "undefined" || !("Notification" in window)) return "unsupported";
    return Notification.permission;
  });
  const [items, setItems] = useState(DEFAULT_NOTIFICATIONS);
  const unreadCount = useMemo(() => items.length, [items.length]);

  async function enableNotifications() {
    if (!("Notification" in window)) {
      setPermission("unsupported");
      return;
    }
    const nextPermission = await Notification.requestPermission();
    setPermission(nextPermission);
    if (nextPermission === "granted") {
      new Notification("AURA notifications enabled", {
        body: "Important system, calendar, and assistant alerts can appear here.",
      });
    }
  }

  function clearOne(id: string) {
    setItems((current) => current.filter((item) => item.id !== id));
  }

  return (
    <section className="notifications-widget-card" aria-label="System notifications">
      <header>
        <div>
          <span>Inbox</span>
          <h3>Notifications</h3>
        </div>
        <strong>{unreadCount}</strong>
      </header>

      <div className="notifications-list">
        {items.length ? items.map((item) => (
          <button key={item.id} type="button" className={`notification-item tone-${item.tone}`} onClick={() => clearOne(item.id)}>
            <i aria-hidden="true" />
            <span>
              <strong>{item.title}</strong>
              <small>{item.body}</small>
            </span>
            <em>{item.time}</em>
          </button>
        )) : (
          <div className="notification-empty">No new notifications</div>
        )}
      </div>

      <button type="button" className="notification-permission-btn" onClick={enableNotifications}>
        {permission === "granted" ? "Notifications enabled" : permission === "denied" ? "Enable in system settings" : "Enable desktop alerts"}
      </button>
    </section>
  );
}
