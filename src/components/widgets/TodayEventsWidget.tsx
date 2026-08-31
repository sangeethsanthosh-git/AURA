import { useState } from "react";

interface EventItem {
  id: string;
  title: string;
  category: string;
  timeRange: string;
  completed?: boolean;
}

interface TodayEventsWidgetProps {
  initialTheme?: "light" | "dark";
}

export function TodayEventsWidget({ initialTheme = "light" }: TodayEventsWidgetProps) {
  const [theme, setTheme] = useState<"light" | "dark">(initialTheme);
  const [events, setEvents] = useState<EventItem[]>([
    {
      id: "e1",
      title: "Meeting with Jen",
      category: "Work",
      timeRange: "9:00 AM\n10:30 AM",
      completed: false,
    },
    {
      id: "e2",
      title: "Dental appointment",
      category: "Personal",
      timeRange: "2:00 PM\n2:30 PM",
      completed: false,
    },
  ]);

  function toggleComplete(id: string) {
    setEvents((prev) =>
      prev.map((e) => (e.id === id ? { ...e, completed: !e.completed } : e))
    );
  }

  return (
    <div
      className={`minimal-events-card minimal-events-card--${theme}`}
      aria-label="Today's Events Widget"
    >
      {/* Top Header Row */}
      <div className="events-card-header">
        <h3 className="events-main-title">Today</h3>
        <div className="events-header-right">
          <span className="events-count-badge">{events.length} events</span>
          <button
            type="button"
            className="events-theme-toggle-btn"
            onClick={() => setTheme((prev) => (prev === "light" ? "dark" : "light"))}
            title={`Switch to ${theme === "light" ? "Dark" : "Light"} mode`}
          >
            {theme === "light" ? "🌙" : "☀️"}
          </button>
        </div>
      </div>

      {/* Events List (Matching Reference Image) */}
      <div className="events-items-list" role="list">
        {events.map((ev) => (
          <div
            key={ev.id}
            className={`event-row-item ${ev.completed ? "completed" : ""}`}
            onClick={() => toggleComplete(ev.id)}
            role="listitem"
          >
            {/* Left Solid Vertical Accent Bar */}
            <div className="event-vertical-bar" />

            <div className="event-content-group">
              <strong className="event-item-title">{ev.title}</strong>
              <span className="event-item-category">{ev.category}</span>
            </div>

            <div className="event-time-group">
              <span className="event-time-line">{ev.timeRange.split("\n")[0]}</span>
              <span className="event-time-line">{ev.timeRange.split("\n")[1]}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

