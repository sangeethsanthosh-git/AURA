import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { auraApi, NewsArticle, WebSearchResult, WeatherCurrentResponse } from "../../services/auraApi";
import { readAppSettings, subscribeToAppSettings } from "../../state/appSettings";
import { MusicWidget } from "./MusicWidget";

interface WorkstationInspectorProps {
  onClose?: () => void;
  onTriggerPrompt?: (prompt: string) => void;
}

type BoardCardId =
  | "music"
  | "profile"
  | "maps"
  | "search"
  | "payment"
  | "weather"
  | "date"
  | "schedule"
  | "news"
  | "assistant"
  | "note";

type CustomNoteCard = {
  id: string;
  title: string;
  text: string;
};

type BoardLayoutItem = {
  x: number;
  y: number;
  w: number;
  h: number;
};

type BoardLayout = Record<string, BoardLayoutItem>;

const PAYMENT_DAYS = [
  { day: 3, label: "Rent", tone: "green", icon: "R" },
  { day: 8, label: "Card", tone: "pink", icon: "C" },
  { day: 13, label: "Phone", tone: "blue", icon: "P" },
  { day: 18, label: "Spotify", tone: "green", icon: "S" },
  { day: 23, label: "Netflix", tone: "red", icon: "N" },
  { day: 28, label: "Cloud", tone: "blue", icon: "CL" },
];

const DEFAULT_BOARD_ORDER: BoardCardId[] = [
  "music",
  "profile",
  "maps",
  "search",
  "payment",
  "weather",
  "date",
  "schedule",
  "news",
  "assistant",
];

const BOARD_LAYOUT_KEY = "aura.dashboard.freeform-layout.v1";
const MIN_CARD_WIDTH = 220;
const MIN_CARD_HEIGHT = 130;

const DEFAULT_BOARD_LAYOUT: BoardLayout = {
  music: { x: 0, y: 0, w: 560, h: 330 },
  profile: { x: 584, y: 0, w: 270, h: 180 },
  maps: { x: 878, y: 0, w: 270, h: 180 },
  search: { x: 584, y: 204, w: 270, h: 190 },
  weather: { x: 878, y: 204, w: 270, h: 190 },
  payment: { x: 0, y: 360, w: 560, h: 380 },
  date: { x: 584, y: 420, w: 270, h: 180 },
  schedule: { x: 584, y: 624, w: 564, h: 190 },
  news: { x: 0, y: 768, w: 560, h: 190 },
  assistant: { x: 584, y: 838, w: 564, h: 190 },
};

function weatherSummary(data?: WeatherCurrentResponse["data"] | null) {
  const weather = data?.formatted_weather;
  return {
    temperature: weather?.temperature ?? "--",
    feelsLike: weather?.feels_like ?? "--",
    location: data?.location?.name || "Local",
    condition: weather?.condition || "Current condition",
  };
}

function readBoardLayout(): BoardLayout {
  try {
    const raw = window.localStorage.getItem(BOARD_LAYOUT_KEY);
    if (!raw) return DEFAULT_BOARD_LAYOUT;
    return { ...DEFAULT_BOARD_LAYOUT, ...(JSON.parse(raw) as BoardLayout) };
  } catch {
    return DEFAULT_BOARD_LAYOUT;
  }
}

function saveBoardLayout(layout: BoardLayout) {
  window.localStorage.setItem(BOARD_LAYOUT_KEY, JSON.stringify(layout));
}

function defaultLayoutFor(index: number): BoardLayoutItem {
  const width = 320;
  const height = 190;
  const gap = 24;
  return {
    x: (index % 3) * (width + gap),
    y: Math.floor(index / 3) * (height + gap),
    w: width,
    h: height,
  };
}

function FloatingBoardCard({
  id,
  layout,
  children,
  onChange,
}: {
  id: string;
  layout: BoardLayoutItem;
  children: ReactNode;
  onChange: (id: string, layout: BoardLayoutItem) => void;
}) {
  const cardRef = useRef<HTMLDivElement | null>(null);
  const dragState = useRef<{ startX: number; startY: number; startLeft: number; startTop: number } | null>(null);

  useEffect(() => {
    const node = cardRef.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => {
      const nextWidth = Math.round(entry.contentRect.width);
      const nextHeight = Math.round(entry.contentRect.height);
      if (Math.abs(nextWidth - layout.w) > 3 || Math.abs(nextHeight - layout.h) > 3) {
        onChange(id, { ...layout, w: nextWidth, h: nextHeight });
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [id, layout, onChange]);

  function handlePointerDown(event: React.PointerEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    if (!target.closest(".board-card-toolbar")) return;
    if (target.closest("button, input, textarea, select, a")) return;
    event.preventDefault();
    dragState.current = {
      startX: event.clientX,
      startY: event.clientY,
      startLeft: layout.x,
      startTop: layout.y,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    event.currentTarget.classList.add("is-floating-dragging");
  }

  function handlePointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!dragState.current) return;
    onChange(id, {
      ...layout,
      x: Math.max(0, dragState.current.startLeft + event.clientX - dragState.current.startX),
      y: Math.max(0, dragState.current.startTop + event.clientY - dragState.current.startY),
    });
  }

  function stopDrag(event: React.PointerEvent<HTMLDivElement>) {
    if (!dragState.current) return;
    dragState.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
    event.currentTarget.classList.remove("is-floating-dragging");
  }

  return (
    <div
      ref={cardRef}
      className="floating-board-card"
      style={{
        left: `${layout.x}px`,
        top: `${layout.y}px`,
        width: `${layout.w}px`,
        height: `${layout.h}px`,
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={stopDrag}
      onPointerCancel={stopDrag}
    >
      {children}
    </div>
  );
}

export function WorkstationInspector({ onClose, onTriggerPrompt }: WorkstationInspectorProps) {
  const [appSettings, setAppSettings] = useState(() => readAppSettings());
  const [weather, setWeather] = useState<WeatherCurrentResponse["data"] | null>(null);
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<WebSearchResult[]>([]);
  const [boardOrder, setBoardOrder] = useState<BoardCardId[]>(DEFAULT_BOARD_ORDER);
  const [boardLayout, setBoardLayout] = useState<BoardLayout>(() => readBoardLayout());
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [customNotes, setCustomNotes] = useState<CustomNoteCard[]>([]);
  const [noteDraftTitle, setNoteDraftTitle] = useState("");
  const [noteDraftText, setNoteDraftText] = useState("");
  const boardRef = useRef<HTMLDivElement | null>(null);
  const today = useMemo(() => new Date(), []);
  const monthLabel = today.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  const days = useMemo(() => Array.from({ length: 31 }, (_, index) => index + 1), []);
  const weatherNow = weatherSummary(weather);
  const profileDisplayName = appSettings.profileName?.trim() || "User";
  const profileInitials = profileDisplayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "U";
  const boardIds = useMemo(() => [...boardOrder, ...customNotes.map((note) => note.id)], [boardOrder, customNotes]);
  const boardHeight = useMemo(() => {
    return Math.max(
      720,
      ...boardIds.map((id, index) => {
        const item = boardLayout[id] || defaultLayoutFor(index);
        return item.y + item.h + 40;
      }),
    );
  }, [boardIds, boardLayout]);

  useEffect(() => {
    saveBoardLayout(boardLayout);
  }, [boardLayout]);

  useEffect(() => {
    const board = boardRef.current;
    if (!board || typeof ResizeObserver === "undefined") return;
    const clampCards = () => {
      const availableWidth = board.clientWidth;
      if (!availableWidth) return;
      setBoardLayout((current) => {
        let changed = false;
        const next = { ...current };
        Object.entries(current).forEach(([id, item]) => {
          const width = Math.min(item.w, Math.max(MIN_CARD_WIDTH, availableWidth));
          const x = Math.max(0, Math.min(item.x, Math.max(0, availableWidth - width)));
          if (width !== item.w || x !== item.x) {
            next[id] = { ...item, w: width, x };
            changed = true;
          }
        });
        return changed ? next : current;
      });
    };
    const observer = new ResizeObserver(clampCards);
    observer.observe(board);
    clampCards();
    return () => observer.disconnect();
  }, []);

  useEffect(() => subscribeToAppSettings(() => {
    setAppSettings(readAppSettings());
  }), []);

  useEffect(() => {
    void auraApi.getWeather().then((response) => {
      if (response.ok) setWeather(response.data);
    }).catch(() => undefined);
    void auraApi.getNews("Technology", "", 3).then((response) => {
      if (response.ok) setNews(response.data.articles || []);
    }).catch(() => undefined);
  }, []);

  async function submitSearch(event: FormEvent) {
    event.preventDefault();
    const clean = searchQuery.trim();
    if (!clean) return;
    const response = await auraApi.webSearch(clean, 3);
    if (response.ok) setSearchResults(response.results);
  }

  function moveCard(id: BoardCardId, direction: -1 | 1) {
    setBoardOrder((current) => {
      const index = current.indexOf(id);
      if (index === -1) return current;
      const nextIndex = index + direction;
      if (nextIndex < 0 || nextIndex >= current.length) return current;
      const copy = [...current];
      const [item] = copy.splice(index, 1);
      copy.splice(nextIndex, 0, item);
      return copy;
    });
  }

  function addCustomNote() {
    const title = noteDraftTitle.trim();
    const text = noteDraftText.trim();
    if (!title && !text) return;
    const noteId = `note-${Date.now()}`;
    setCustomNotes((current) => [
      { id: noteId, title: title || "Custom widget", text: text || "Add your own quick info here." },
      ...current,
    ]);
    setBoardLayout((current) => ({ ...current, [noteId]: defaultLayoutFor(boardIds.length) }));
    setNoteDraftTitle("");
    setNoteDraftText("");
    setShowAddMenu(false);
  }

  function updateCardLayout(id: string, next: BoardLayoutItem) {
    setBoardLayout((current) => ({
      ...current,
      [id]: {
        x: Math.round(next.x),
        y: Math.round(next.y),
        w: Math.max(MIN_CARD_WIDTH, Math.round(next.w)),
        h: Math.max(MIN_CARD_HEIGHT, Math.round(next.h)),
      },
    }));
  }

  function resetBoardLayout() {
    setBoardOrder(DEFAULT_BOARD_ORDER);
    setBoardLayout(DEFAULT_BOARD_LAYOUT);
  }

  function renderCard(id: BoardCardId) {
    if (id === "music") {
      return (
        <section className="multi-card music-widget-card">
          <div className="board-card-toolbar">
            <span>Music</span>
            <div className="board-card-actions">
              <button type="button" title="Move up" onClick={() => moveCard(id, -1)}>▲</button>
              <button type="button" title="Move down" onClick={() => moveCard(id, 1)}>▼</button>
            </div>
          </div>
          <MusicWidget />
        </section>
      );
    }

    if (id === "profile") {
      return (
        <section className="multi-card profile-card">
          <div className="board-card-toolbar">
            <span>Profile</span>
            <div className="board-card-actions">
              <button type="button" title="Move up" onClick={() => moveCard(id, -1)}>▲</button>
              <button type="button" title="Move down" onClick={() => moveCard(id, 1)}>▼</button>
            </div>
          </div>
          <div className="profile-avatar-card">
            {appSettings.avatarImage ? <img src={appSettings.avatarImage} alt="" /> : profileInitials}
          </div>
          <strong>{profileDisplayName}</strong>
          <small>Ready session</small>
        </section>
      );
    }

    if (id === "maps") {
      return (
        <section className="multi-card mini-map-card" onClick={() => window.aura?.media.openExternal("https://www.google.com/maps")}>
          <div className="board-card-toolbar">
            <span>Maps</span>
            <div className="board-card-actions">
              <button type="button" title="Move up" onClick={() => moveCard(id, -1)}>▲</button>
              <button type="button" title="Move down" onClick={() => moveCard(id, 1)}>▼</button>
            </div>
          </div>
          <div className="map-grid-bg" />
          <span className="map-pin">AURA</span>
          <strong>Google Maps</strong>
        </section>
      );
    }

    if (id === "search") {
      return (
        <section className="multi-card search-mini-card">
          <div className="board-card-toolbar">
            <span>Search</span>
            <div className="board-card-actions">
              <button type="button" title="Move up" onClick={() => moveCard(id, -1)}>▲</button>
              <button type="button" title="Move down" onClick={() => moveCard(id, 1)}>▼</button>
            </div>
          </div>
          <form onSubmit={submitSearch}>
            <input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Mini Google search" />
            <button type="submit" title="Search">Go</button>
          </form>
          {searchResults.length === 0 ? <span>Search the web from here</span> : searchResults.map((result) => (
            <button key={result.url} type="button" onClick={() => window.aura?.media.openExternal(result.url)}>
              {result.title}
            </button>
          ))}
        </section>
      );
    }

    if (id === "payment") {
      return (
        <section className="multi-card payment-card">
          <div className="board-card-toolbar">
            <span>Payments</span>
            <div className="board-card-actions">
              <button type="button" title="Move up" onClick={() => moveCard(id, -1)}>▲</button>
              <button type="button" title="Move down" onClick={() => moveCard(id, 1)}>▼</button>
            </div>
          </div>
          <strong>Scheduled Recurring Payments</strong>
          <span>Budget your monthly expenses in advance or schedule repeat payments.</span>
          <div className="payment-calendar-grid">
            {days.map((day) => {
              const item = PAYMENT_DAYS.find((payment) => payment.day === day);
              return (
                <i key={day} title={item?.label}>
                  <span>{day}</span>
                  {item && <b className={`pay-${item.tone}`}>{item.icon}</b>}
                </i>
              );
            })}
          </div>
        </section>
      );
    }

    if (id === "weather") {
      return (
        <section className="multi-card weather-now-card">
          <div className="board-card-toolbar">
            <span>Weather</span>
            <div className="board-card-actions">
              <button type="button" title="Move up" onClick={() => moveCard(id, -1)}>▲</button>
              <button type="button" title="Move down" onClick={() => moveCard(id, 1)}>▼</button>
            </div>
          </div>
          <strong>
            <b>{weatherNow.temperature}</b>
            <span>now in</span>
            {weatherNow.location}
          </strong>
          <small>feels {weatherNow.feelsLike} / {weatherNow.condition}</small>
        </section>
      );
    }

    if (id === "date") {
      return (
        <section className="multi-card date-card">
          <div className="board-card-toolbar">
            <span>Date</span>
            <div className="board-card-actions">
              <button type="button" title="Move up" onClick={() => moveCard(id, -1)}>▲</button>
              <button type="button" title="Move down" onClick={() => moveCard(id, 1)}>▼</button>
            </div>
          </div>
          <span>{monthLabel}</span>
          <strong>{String(today.getDate()).padStart(2, "0")}</strong>
          <small>{today.toLocaleDateString(undefined, { weekday: "long" })}</small>
        </section>
      );
    }

    if (id === "schedule") {
      return (
        <section className="multi-card schedule-card">
          <div className="board-card-toolbar">
            <span>Schedule</span>
            <div className="board-card-actions">
              <button type="button" title="Move up" onClick={() => moveCard(id, -1)}>▲</button>
              <button type="button" title="Move down" onClick={() => moveCard(id, 1)}>▼</button>
            </div>
          </div>
          <strong>Today</strong>
          <button type="button">Product design review</button>
          <button type="button">New coding feature</button>
          <button type="button">Focus block</button>
        </section>
      );
    }

    if (id === "news") {
      return (
        <section className="multi-card news-strip-card">
          <div className="board-card-toolbar">
            <span>News</span>
            <div className="board-card-actions">
              <button type="button" title="Move up" onClick={() => moveCard(id, -1)}>▲</button>
              <button type="button" title="Move down" onClick={() => moveCard(id, 1)}>▼</button>
            </div>
          </div>
          {news.length === 0 ? <p className="board-card-empty">No fresh news yet.</p> : news.map((article) => (
            <button key={article.id} type="button" onClick={() => window.aura?.media.openExternal(article.url)} className={article.image_url ? "news-strip-item has-image" : "news-strip-item"}>
              {article.image_url && <img src={article.image_url} alt="" aria-hidden="true" />}
              <span>
                <strong>{article.title}</strong>
                <small>{article.source}</small>
              </span>
            </button>
          ))}
        </section>
      );
    }

    if (id === "assistant") {
      return (
        <section className="multi-card assistant-actions-card">
          <div className="board-card-toolbar">
            <span>Assistant</span>
            <div className="board-card-actions">
              <button type="button" title="Move up" onClick={() => moveCard(id, -1)}>▲</button>
              <button type="button" title="Move down" onClick={() => moveCard(id, 1)}>▼</button>
            </div>
          </div>
          <strong>Assistant Tools</strong>
          <button type="button" onClick={() => onTriggerPrompt?.("/screen inspect the active window")}>Screen vision</button>
          <button type="button" onClick={() => onTriggerPrompt?.("recall useful memories for this workspace")}>Memory recall</button>
          <button type="button" onClick={() => onTriggerPrompt?.("open an app for me")}>Open app</button>
        </section>
      );
    }

    return null;
  }

  return (
    <aside className="multi-panel-workstation" aria-label="Assistant cards dashboard">
      <header className="multi-panel-rail">
        <span className="rail-dot rail-dot-active" />
        <button type="button" title="Home">H</button>
        <button type="button" title="Search">S</button>
        <button type="button" title="History">R</button>
        <button type="button" title="Media">M</button>
        {onClose && <button type="button" onClick={onClose} title="Close">x</button>}
      </header>

      <div className="multi-card-board-tools">
        <button type="button" className="widget-add-drawer-btn active" onClick={() => setShowAddMenu((prev) => !prev)}>+ Add more</button>
        <button type="button" className="widget-add-drawer-btn" onClick={resetBoardLayout}>Reset board</button>
      </div>

      {showAddMenu && (
        <div className="widget-catalog-drawer widget-catalog-drawer--board">
          <div className="catalog-drawer-header">
            <span className="catalog-drawer-title">Board widgets</span>
            <button type="button" className="catalog-close-btn" onClick={() => setShowAddMenu(false)}>✕</button>
          </div>
          <div className="catalog-items-grid">
            <button type="button" className="catalog-item-card" onClick={() => {
              const noteId = `note-${Date.now()}`;
              setCustomNotes((current) => [{ id: noteId, title: "Quick note", text: "Drag me around the board." }, ...current]);
              setBoardLayout((current) => ({ ...current, [noteId]: defaultLayoutFor(boardIds.length) }));
            }}>
              <div className="catalog-item-icon">📝</div>
              <div className="catalog-item-info">
                <strong>Custom note</strong>
                <p>Create a personal tile for reminders or ideas.</p>
              </div>
              <span className="catalog-toggle-btn enabled">+ Add</span>
            </button>
            <div className="catalog-item-card catalog-item-card--form">
              <div className="catalog-item-info">
                <strong>Make your own</strong>
                <p>Name a quick card and pin it to the dashboard.</p>
              </div>
              <input value={noteDraftTitle} onChange={(e) => setNoteDraftTitle(e.target.value)} placeholder="Card title" />
              <input value={noteDraftText} onChange={(e) => setNoteDraftText(e.target.value)} placeholder="Card text" />
              <button type="button" className="catalog-toggle-btn enabled" onClick={addCustomNote}>Add widget</button>
            </div>
          </div>
        </div>
      )}

      <div ref={boardRef} className="multi-card-grid multi-card-freeform-board" style={{ height: `${boardHeight}px` }}>
        {boardOrder.map((id, index) => (
          <FloatingBoardCard
            key={id}
            id={id}
            layout={boardLayout[id] || defaultLayoutFor(index)}
            onChange={updateCardLayout}
          >
            <div className="multi-card-shell">
              {renderCard(id)}
            </div>
          </FloatingBoardCard>
        ))}
        {customNotes.map((note, index) => (
          <FloatingBoardCard
            key={note.id}
            id={note.id}
            layout={boardLayout[note.id] || defaultLayoutFor(boardOrder.length + index)}
            onChange={updateCardLayout}
          >
            <section className="multi-card note-card">
              <div className="board-card-toolbar">
                <span>{note.title}</span>
                <div className="board-card-actions">
                  <button type="button" onClick={() => setCustomNotes((current) => current.filter((item) => item.id !== note.id))}>✕</button>
                </div>
              </div>
              <p>{note.text}</p>
            </section>
          </FloatingBoardCard>
        ))}
      </div>
    </aside>
  );
}

