import { FormEvent, useEffect, useMemo, useState } from "react";

type CalendarView = "month" | "week" | "day" | "payments";
type CalendarTone = "green" | "neutral" | "amber" | "blue" | "pink";

interface CalendarEvent {
  id: string;
  title: string;
  date: string;
  start: string;
  end: string;
  calendar: string;
  location: string;
  tone: CalendarTone;
  guests: string[];
}

type DraftEvent = Omit<CalendarEvent, "id" | "guests"> & { id?: string };

const initialEvents: CalendarEvent[] = [
  { id: "event-1", date: "2025-05-03", start: "10:00", end: "11:30", calendar: "Learn Design", title: "Product design review", location: "AURA Calendar", tone: "green", guests: ["Jaroslav", "Paulina"] },
  { id: "event-2", date: "2025-05-03", start: "13:30", end: "14:30", calendar: "Working", title: "New SAI coding feature", location: "SAI", tone: "neutral", guests: ["Alex"] },
  { id: "event-3", date: "2025-05-03", start: "17:30", end: "17:45", calendar: "Break", title: "Espresso time with Kate", location: "Personal", tone: "amber", guests: ["Kate"] },
  { id: "event-4", date: "2025-05-03", start: "18:00", end: "18:30", calendar: "Design session", title: "Design new layout for SAI app", location: "SAI", tone: "blue", guests: ["Martin", "Paulina"] },
  { id: "event-5", date: "2025-05-04", start: "18:30", end: "21:30", calendar: "Talk with sale", title: "Manage client handoff notes", location: "Google Meet", tone: "pink", guests: ["Jaroslav"] },
];

const calendars = ["Learn Design", "Working", "Break", "Design session", "Talk with sale", "Scheduled Payments"];
const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const weekLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const calendarStorageKey = "aura.schedule.events.v1";
type RecurringPaymentTemplate = {
  day: number;
  name: string;
  amount: string;
  tone: CalendarTone;
};

const recurringPaymentTemplates: RecurringPaymentTemplate[] = [
  { day: 3, name: "Rent", amount: "$850", tone: "green" },
  { day: 8, name: "Credit card", amount: "$240", tone: "pink" },
  { day: 13, name: "Phone", amount: "$35", tone: "blue" },
  { day: 18, name: "Spotify", amount: "$11", tone: "green" },
  { day: 23, name: "Netflix", amount: "$16", tone: "pink" },
  { day: 28, name: "Cloud tools", amount: "$42", tone: "blue" },
];

const toneOrder: CalendarTone[] = ["green", "blue", "amber", "pink", "neutral"];

function toDateKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function fromDateKey(key: string): Date {
  const [year, month, day] = key.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function addDays(date: Date, count: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + count);
  return next;
}

function addMonths(date: Date, count: number): Date {
  const next = new Date(date);
  next.setMonth(next.getMonth() + count);
  return next;
}

function startOfWeek(date: Date): Date {
  return addDays(date, -date.getDay());
}

function formatMonth(date: Date): string {
  return `${monthNames[date.getMonth()]} ${date.getFullYear()}`;
}

function buildRecurringPaymentEvents(month: Date): CalendarEvent[] {
  return recurringPaymentTemplates.map((payment, index) => {
    const paymentDate = new Date(month.getFullYear(), month.getMonth(), payment.day);
    return {
      id: `payment-${month.getFullYear()}-${String(month.getMonth() + 1).padStart(2, "0")}-${payment.day}-${index}`,
      title: payment.name,
      date: toDateKey(paymentDate),
      start: "09:00",
      end: "09:15",
      calendar: "Scheduled Payments",
      location: payment.amount,
      tone: payment.tone,
      guests: ["AURA"],
    };
  });
}

function dayTone(events: CalendarEvent[]) {
  return toneOrder.find((candidate) => events.some((event) => event.tone === candidate)) || "neutral";
}

function makeDraft(date: string, source?: CalendarEvent): DraftEvent {
  return {
    id: source?.id,
    title: source?.title || "",
    date,
    start: source?.start || "09:00",
    end: source?.end || "10:00",
    calendar: source?.calendar || "Working",
    location: source?.location || "AURA Calendar",
    tone: source?.tone || "blue",
  };
}

function loadStoredEvents(): CalendarEvent[] {
  if (typeof window === "undefined") return initialEvents;

  try {
    const stored = window.localStorage.getItem(calendarStorageKey);
    if (!stored) return initialEvents;
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return initialEvents;
    return parsed.filter((event): event is CalendarEvent =>
      typeof event?.id === "string" &&
      typeof event?.title === "string" &&
      typeof event?.date === "string" &&
      typeof event?.start === "string" &&
      typeof event?.end === "string" &&
      typeof event?.calendar === "string" &&
      typeof event?.location === "string" &&
      typeof event?.tone === "string" &&
      Array.isArray(event?.guests)
    );
  } catch {
    return initialEvents;
  }
}

export function ScheduleCalendarView() {
  const [view, setView] = useState<CalendarView>("week");
  const [selectedDate, setSelectedDate] = useState("2025-05-03");
  const [visibleMonth, setVisibleMonth] = useState(fromDateKey("2025-05-03"));
  const [events, setEvents] = useState<CalendarEvent[]>(loadStoredEvents);
  const [draft, setDraft] = useState<DraftEvent | null>(null);
  const [search, setSearch] = useState("");
  const [enabledCalendars, setEnabledCalendars] = useState<Record<string, boolean>>(
    Object.fromEntries(calendars.map((name) => [name, true]))
  );

  const selectedDateObj = fromDateKey(selectedDate);
  const monthStart = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1);
  const miniStart = startOfWeek(monthStart);
  const miniCalendarDays = useMemo(() => Array.from({ length: 42 }, (_, index) => addDays(miniStart, index)), [miniStart.getTime()]);
  const recurringPaymentEvents = useMemo(() => buildRecurringPaymentEvents(visibleMonth), [visibleMonth.getTime()]);
  const calendarEvents = useMemo(
    () => [...events, ...recurringPaymentEvents].sort((a, b) => `${a.date} ${a.start}`.localeCompare(`${b.date} ${b.start}`)),
    [events, recurringPaymentEvents]
  );

  const visibleDays = useMemo(() => {
    if (view === "day") return [selectedDateObj];
    if (view === "month") {
      return Array.from({ length: 42 }, (_, index) => addDays(miniStart, index));
    }
    const weekStart = startOfWeek(selectedDateObj);
    return Array.from({ length: 7 }, (_, index) => addDays(weekStart, index));
  }, [miniStart.getTime(), selectedDateObj.getTime(), view, visibleMonth]);

  const filteredEvents = useMemo(() => {
    const clean = search.trim().toLowerCase();
    return calendarEvents
      .filter((event) => enabledCalendars[event.calendar] !== false)
      .filter((event) => !clean || [event.title, event.calendar, event.location].some((value) => value.toLowerCase().includes(clean)))
      .sort((a, b) => `${a.date} ${a.start}`.localeCompare(`${b.date} ${b.start}`));
  }, [calendarEvents, enabledCalendars, search]);

  const selectedEvents = filteredEvents.filter((event) => event.date === selectedDate);
  const upcomingEvents = useMemo(() => {
    return filteredEvents.filter((event) => event.date >= selectedDate).slice(0, 5);
  }, [filteredEvents, selectedDate]);
  const recurringPaymentsForMonth = recurringPaymentTemplates.map((payment) => ({
    ...payment,
    date: toDateKey(new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), payment.day)),
  }));
  const busyMinutes = selectedEvents.reduce((total, event) => {
    const [startHour, startMinute] = event.start.split(":").map(Number);
    const [endHour, endMinute] = event.end.split(":").map(Number);
    return total + Math.max(0, (endHour * 60 + endMinute) - (startHour * 60 + startMinute));
  }, 0);
  const busiestCalendar = selectedEvents.reduce<Record<string, number>>((count, event) => {
    count[event.calendar] = (count[event.calendar] || 0) + 1;
    return count;
  }, {});
  const topCalendar = Object.entries(busiestCalendar).sort((a, b) => b[1] - a[1])[0]?.[0] || "Open day";

  useEffect(() => {
    window.localStorage.setItem(calendarStorageKey, JSON.stringify(events));
  }, [events]);

  function eventsForDate(date: Date): CalendarEvent[] {
    return filteredEvents.filter((event) => event.date === toDateKey(date));
  }

  function selectDate(date: Date) {
    setSelectedDate(toDateKey(date));
    setVisibleMonth(date);
  }

  function movePeriod(direction: -1 | 1) {
    if (view === "month") {
      const next = addMonths(visibleMonth, direction);
      setVisibleMonth(next);
      setSelectedDate(toDateKey(new Date(next.getFullYear(), next.getMonth(), 1)));
      return;
    }
    const next = addDays(selectedDateObj, (view === "week" ? 7 : 1) * direction);
    selectDate(next);
  }

  function jumpToday() {
    selectDate(new Date());
  }

  function saveEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft?.title.trim()) return;
    setEvents((current) => {
      if (draft.id) {
        return current.map((item) => item.id === draft.id ? { ...item, ...draft, title: draft.title.trim() } : item);
      }
      return [...current, { ...draft, id: `event-${Date.now()}`, title: draft.title.trim(), guests: ["AURA"] }];
    });
    setSelectedDate(draft.date);
    setVisibleMonth(fromDateKey(draft.date));
    setDraft(null);
  }

  function deleteEvent(id: string) {
    setEvents((current) => current.filter((event) => event.id !== id));
    setDraft(null);
  }

  return (
    <div className="schedule-ref-shell" aria-label="AURA Schedule">
      <aside className="schedule-ref-left">
        <div className="schedule-side-logo-stack" aria-hidden="true">
          <span className="schedule-round-logo">A</span>
          <span className="schedule-round-logo schedule-round-logo-soft">S</span>
        </div>

        <div className="schedule-mini-panel">
          <header className="schedule-mini-header">
            <label className="schedule-check-title">
              <input type="checkbox" checked readOnly />
              <span>Calendar</span>
            </label>
            <button type="button" className="schedule-icon-button" title="Create new event" onClick={() => setDraft(makeDraft(selectedDate))}>+</button>
          </header>

          <div className="schedule-search-box">
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search events" />
          </div>

          <div className="schedule-mini-weekdays">
            {weekLabels.map((label) => <span key={label}>{label.slice(0, 2)}</span>)}
          </div>
          <div className="schedule-mini-grid">
              {miniCalendarDays.map((date) => {
                const key = toDateKey(date);
                const dayEvents = eventsForDate(date);
                const tone = dayTone(dayEvents);
                return (
                  <button
                    key={key}
                    type="button"
                    className={`${key === selectedDate ? "active" : ""} ${date.getMonth() !== visibleMonth.getMonth() ? "muted" : ""} ${dayEvents.length > 0 ? `has-events tone-${tone}` : ""}`}
                    onClick={() => selectDate(date)}
                  >
                    {date.getDate()}
                  </button>
                );
              })}
          </div>
        </div>

        <section className="schedule-side-section">
          <header>
            <strong>Events</strong>
            <button type="button" title="Create new event" onClick={() => setDraft(makeDraft(selectedDate))}>+</button>
          </header>
          {selectedEvents.length === 0 && <p className="schedule-empty-note">No events for this day.</p>}
          {selectedEvents.slice(0, 4).map((event, index) => (
            <button className="schedule-person-row" key={event.id} type="button" onClick={() => setDraft(makeDraft(event.date, event))}>
              <span className={`schedule-avatar avatar-${(index % 4) + 1}`} />
              <span>{event.title}</span>
              <small>{event.start}</small>
            </button>
          ))}
        </section>

        <section className="schedule-side-section">
          <header><strong>Calendars</strong></header>
          {calendars.map((name) => (
            <label className="schedule-task-row" key={name}>
              <span>{name}</span>
              <input
                type="checkbox"
                checked={enabledCalendars[name]}
                onChange={() => setEnabledCalendars((current) => ({ ...current, [name]: !current[name] }))}
              />
            </label>
          ))}
        </section>

        <button type="button" className="schedule-floating-add" title="Create new event" onClick={() => setDraft(makeDraft(selectedDate))}>+</button>
      </aside>

      <main className="schedule-ref-agenda">
        <header className="schedule-ref-topbar">
          <div className="schedule-title-cluster">
            <h2>{formatMonth(visibleMonth)}</h2>
            <span>{selectedEvents.length} events selected</span>
          </div>
          <div className="schedule-toolbar">
            <button type="button" onClick={() => movePeriod(-1)} title="Previous">‹</button>
            <button type="button" onClick={jumpToday}>Today</button>
            <button type="button" onClick={() => movePeriod(1)} title="Next">›</button>
            <div className="schedule-view-switcher">
              {(["month", "week", "day"] as CalendarView[]).map((mode) => (
                <button key={mode} type="button" className={view === mode ? "active" : ""} onClick={() => setView(mode)}>
                  {mode}
                </button>
              ))}
            </div>
            <button type="button" className={view === "payments" ? "active" : ""} onClick={() => setView("payments")}>Payments</button>
            <button type="button" className="schedule-share-button" onClick={() => setDraft(makeDraft(selectedDate))}>Create new event</button>
          </div>
        </header>

        {view === "payments" ? (
          <div className="schedule-payments-board">
            <section className="schedule-payments-card">
              <h3>Scheduled Recurring Payments</h3>
              <p>Budget monthly expenses in advance and keep calendar reminders visible.</p>
              <div className="schedule-payment-weekdays">
                {["M", "T", "W", "T", "F", "S", "S"].map((label, index) => <span key={`${label}-${index}`}>{label}</span>)}
              </div>
              <div className="schedule-payment-days">
                {Array.from({ length: 31 }, (_, index) => index + 1).map((day) => {
                  const payment = recurringPaymentTemplates.find((item) => item.day === day);
                  return (
                    <button key={day} type="button" className={payment ? `has-payment pay-${payment.tone}` : ""} title={payment ? `${payment.name} ${payment.amount}` : `Day ${day}`}>
                      {day}
                      {payment && <span>{payment.name.slice(0, 1)}</span>}
                    </button>
                  );
                })}
              </div>
            </section>
            <section className="schedule-payment-list">
              <header>
                <strong>This month</strong>
                <span>{recurringPaymentsForMonth.length} recurring</span>
              </header>
              {recurringPaymentsForMonth.map((payment) => (
                <article key={payment.name} className={`payment-list-row pay-${payment.tone}`}>
                  <span>{fromDateKey(payment.date).getDate()}</span>
                  <strong>{payment.name}</strong>
                  <small>{payment.amount}</small>
                </article>
              ))}
            </section>
          </div>
        ) : view === "month" ? (
          <div className="schedule-month-board">
            <div className="schedule-month-weekdays">
              {weekLabels.map((label) => <span key={label}>{label}</span>)}
            </div>
            <div className="schedule-month-grid">
              {miniCalendarDays.map((date) => {
                const key = toDateKey(date);
                const dayEvents = eventsForDate(date);
                const tone = dayTone(dayEvents);
                return (
                  <button
                    key={key}
                    type="button"
                    className={`schedule-month-cell ${selectedDate === key ? "selected" : ""} ${date.getMonth() !== visibleMonth.getMonth() ? "muted" : ""} ${dayEvents.length > 0 ? `has-events tone-${tone}` : ""}`}
                    onClick={() => selectDate(date)}
                    onDoubleClick={() => setDraft(makeDraft(key))}
                  >
                    <span className="schedule-month-date">{date.getDate()}</span>
                    {dayEvents.length > 0 && <span className="schedule-month-tone-dot" aria-hidden="true" />}
                    <span className="schedule-month-events">
                      {dayEvents.slice(0, 3).map((event) => (
                        <span className={`schedule-month-event tone-${event.tone}`} key={event.id}>
                          <strong>{event.start}</strong>
                          {event.title}
                        </span>
                      ))}
                      {dayEvents.length > 3 && <span className="schedule-month-more">+{dayEvents.length - 3} more</span>}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          <div className={`schedule-agenda-scroll schedule-agenda-scroll-${view}`}>
            {visibleDays.map((date) => {
              const key = toDateKey(date);
              const dayEvents = eventsForDate(date);
              return (
                <section key={key} className={`schedule-day-slab ${selectedDate === key ? "selected" : ""}`} onClick={() => selectDate(date)}>
                  <div className="schedule-day-number">
                    <span>{String(date.getDate()).padStart(2, "0")}</span>
                    <strong>{weekLabels[date.getDay()]}</strong>
                  </div>

                  <div className="schedule-day-events">
                    {selectedDate === key && <div className="schedule-now-line"><span>Selected day</span></div>}
                    {dayEvents.length === 0 && <div className="schedule-empty-slot">There is no meeting yet</div>}
                    {dayEvents.map((event) => (
                      <article className={`schedule-agenda-card tone-${event.tone}`} key={event.id}>
                        <div className="schedule-card-time">
                          <strong>{event.start}</strong>
                          <span>{event.end}</span>
                        </div>
                        <button
                          type="button"
                          className="schedule-card-body"
                          onClick={(click) => {
                            click.stopPropagation();
                            setDraft(makeDraft(event.date, event));
                          }}
                        >
                          <small>{event.calendar}</small>
                          <h3>{event.title}</h3>
                          <span>{event.location}</span>
                        </button>
                        <div className="schedule-card-people">
                          {event.guests.slice(0, 2).map((guest, index) => (
                            <span key={guest} className={`schedule-avatar avatar-${(index % 4) + 1}`} />
                          ))}
                        </div>
                      </article>
                    ))}
                    <button type="button" className="schedule-inline-add" title="Create new event" onClick={(click) => {
                      click.stopPropagation();
                      setDraft(makeDraft(key));
                    }}>+</button>
                  </div>
                </section>
              );
            })}
          </div>
        )}
      </main>

      <aside className="schedule-ref-planner">
        <header className="schedule-planner-header">
          <div>
            <h2>Day Planner</h2>
            <span>{selectedDateObj.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}</span>
          </div>
          <button type="button" onClick={() => setDraft(makeDraft(selectedDate))}>+</button>
        </header>

        <section className="planner-focus-card">
          <span className="planner-kicker">Selected Day</span>
          <strong>{String(selectedDateObj.getDate()).padStart(2, "0")}</strong>
          <p>{selectedEvents.length ? `${selectedEvents.length} events planned` : "No events yet"}</p>
        </section>

        <div className="planner-metrics-grid">
          <section className="planner-metric-card">
            <span>Busy time</span>
            <strong>{Math.floor(busyMinutes / 60)}h {busyMinutes % 60}m</strong>
          </section>
          <section className="planner-metric-card">
            <span>Focus</span>
            <strong>{topCalendar}</strong>
          </section>
        </div>

        <section className="planner-side-section">
          <header>
            <strong>Today's Agenda</strong>
            <button type="button" onClick={() => setDraft(makeDraft(selectedDate))}>Add</button>
          </header>
          {selectedEvents.length === 0 && <p>No events for this day.</p>}
          {selectedEvents.map((event) => (
            <button key={event.id} type="button" className={`planner-agenda-row tone-${event.tone}`} onClick={() => setDraft(makeDraft(event.date, event))}>
              <span>{event.start}</span>
              <strong>{event.title}</strong>
              <small>{event.location}</small>
            </button>
          ))}
        </section>

        <section className="planner-side-section">
          <header><strong>Coming Up</strong></header>
          {upcomingEvents.length === 0 && <p>No upcoming events.</p>}
          {upcomingEvents.map((event) => (
            <button key={event.id} type="button" className="planner-upcoming-row" onClick={() => {
              setSelectedDate(event.date);
              setVisibleMonth(fromDateKey(event.date));
            }}>
              <span>{fromDateKey(event.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span>
              <strong>{event.title}</strong>
            </button>
          ))}
        </section>

        <footer className="planner-quick-actions">
          <button type="button" onClick={jumpToday}>Today</button>
          <button type="button" onClick={() => setView("day")}>Day</button>
          <button type="button" onClick={() => setView("week")}>Week</button>
        </footer>
      </aside>

      {draft && (
        <div className="schedule-event-dialog-backdrop" role="presentation" onMouseDown={() => setDraft(null)}>
          <form className="schedule-event-dialog" aria-label="Event editor" onSubmit={saveEvent} onMouseDown={(event) => event.stopPropagation()}>
            <header>
              <h2>{draft.id ? "Edit event" : "Create event"}</h2>
              <button type="button" onClick={() => setDraft(null)} title="Close">x</button>
            </header>
            <label>
              Title
              <input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="Add title" autoFocus />
            </label>
            <div className="schedule-dialog-grid">
              <label>
                Date
                <input type="date" value={draft.date} onChange={(event) => setDraft({ ...draft, date: event.target.value })} />
              </label>
              <label>
                Calendar
                <select value={draft.calendar} onChange={(event) => setDraft({ ...draft, calendar: event.target.value })}>
                  {calendars.map((name) => <option key={name}>{name}</option>)}
                </select>
              </label>
              <label>
                Start
                <input type="time" value={draft.start} onChange={(event) => setDraft({ ...draft, start: event.target.value })} />
              </label>
              <label>
                End
                <input type="time" value={draft.end} onChange={(event) => setDraft({ ...draft, end: event.target.value })} />
              </label>
            </div>
            <label>
              Location
              <input value={draft.location} onChange={(event) => setDraft({ ...draft, location: event.target.value })} placeholder="Add location or call link" />
            </label>
            <label>
              Color
              <select value={draft.tone} onChange={(event) => setDraft({ ...draft, tone: event.target.value as CalendarTone })}>
                <option value="blue">Blue</option>
                <option value="green">Green</option>
                <option value="amber">Amber</option>
                <option value="pink">Pink</option>
                <option value="neutral">Neutral</option>
              </select>
            </label>
            <footer>
              {draft.id && <button type="button" className="schedule-delete-button" onClick={() => deleteEvent(draft.id || "")}>Delete</button>}
              <button type="button" onClick={() => setDraft(null)}>Cancel</button>
              <button type="submit" className="schedule-save-button" disabled={!draft.title.trim()}>Save</button>
            </footer>
          </form>
        </div>
      )}
    </div>
  );
}
