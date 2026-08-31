import { ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { MusicWidget } from "./MusicWidget";
import { WeatherWidget } from "./WeatherWidget";
import { NewsWidget } from "./NewsWidget";
import { TodayEventsWidget } from "./TodayEventsWidget";
import { YearProgressWidget } from "./YearProgressWidget";
import { AuraCompanionWidget } from "./AuraCompanionWidget";
import { ChecklistIcon, PlusIcon } from "../ui/Icons";

export type WidgetCategory = "media" | "info" | "space";

export type WidgetId =
  | "music"
  | "weather"
  | "events"
  | "year"
  | "news"
  | "companion"
  | "lighting"
  | "tasks";

interface WidgetMeta {
  id: WidgetId;
  name: string;
  category: WidgetCategory;
  icon: string;
  description: string;
}

const WIDGET_CATALOG: WidgetMeta[] = [
  { id: "music", name: "Spotify & Music", category: "media", icon: "🎵", description: "Live media player and Spotify sync" },
  { id: "weather", name: "Minimal Weather", category: "info", icon: "🌦️", description: "Compact weather card with forecast" },
  { id: "events", name: "Today's Events", category: "info", icon: "📅", description: "Clean schedule list" },
  { id: "year", name: "Year Progress", category: "space", icon: "⏳", description: "Year progress matrix" },
  { id: "news", name: "Tech & AI News", category: "info", icon: "📰", description: "Curated news feed" },
  { id: "companion", name: "Aura Companion", category: "space", icon: "🧠", description: "Background companion widget" },
  { id: "lighting", name: "Smart Lighting", category: "space", icon: "💡", description: "Ambient color controller" },
  { id: "tasks", name: "Tasks & Reminders", category: "space", icon: "✅", description: "Daily checklist" },
];

interface TaskItem {
  id: string;
  title: string;
  time: string;
  completed: boolean;
  priority: "high" | "normal";
}

type WidgetPlacement = { x: number; y: number; w: number; h: number };

const LAYOUT_KEY = "aura.right-widgets.freeform-layout.v1";
const MIN_W = 240;
const MIN_H = 140;

function readLayout(): Record<string, WidgetPlacement> {
  try {
    const raw = window.localStorage.getItem(LAYOUT_KEY);
    return raw ? (JSON.parse(raw) as Record<string, WidgetPlacement>) : {};
  } catch {
    return {};
  }
}

function saveLayout(layout: Record<string, WidgetPlacement>) {
  window.localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout));
}

function defaultPlacement(index: number): WidgetPlacement {
  return {
    x: (index % 2) * 360,
    y: Math.floor(index / 2) * 260,
    w: 320,
    h: 210,
  };
}

function floatingSize(size: string) {
  if (size === "wide") return { w: 520, h: 330 };
  if (size === "large" || size === "full") return { w: 400, h: 280 };
  return { w: 320, h: 210 };
}

function FloatingCard({
  id,
  title,
  placement,
  onMove,
  onResize,
  onRemove,
  children,
}: {
  id: WidgetId;
  title: string;
  placement: WidgetPlacement;
  onMove: (id: WidgetId, next: WidgetPlacement) => void;
  onResize: (id: WidgetId, next: WidgetPlacement) => void;
  onRemove: (id: WidgetId) => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const dragState = useRef<{ x: number; y: number; left: number; top: number } | null>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => {
      const next = {
        x: placement.x,
        y: placement.y,
        w: Math.max(MIN_W, Math.round(entry.contentRect.width)),
        h: Math.max(MIN_H, Math.round(entry.contentRect.height)),
      };
      if (next.w !== placement.w || next.h !== placement.h) onResize(id, next);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [id, onResize, placement]);

  function beginMove(event: React.PointerEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    if (!target.closest(".widget-dock-drag-bar")) return;
    if (target.closest("button, input, textarea, select, a")) return;
    dragState.current = { x: event.clientX, y: event.clientY, left: placement.x, top: placement.y };
    event.currentTarget.setPointerCapture(event.pointerId);
    event.preventDefault();
  }

  function handleMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!dragState.current) return;
    onMove(id, {
      ...placement,
      x: Math.max(0, dragState.current.left + event.clientX - dragState.current.x),
      y: Math.max(0, dragState.current.top + event.clientY - dragState.current.y),
    });
  }

  function stopMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!dragState.current) return;
    dragState.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
  }

  return (
    <div
      ref={ref}
      className="reorderable-widget-wrapper resizable-length-card widget-card-floating"
      style={{
        left: `${placement.x}px`,
        top: `${placement.y}px`,
        width: `${placement.w}px`,
        height: `${placement.h}px`,
      }}
      onPointerDown={beginMove}
      onPointerMove={handleMove}
      onPointerUp={stopMove}
      onPointerCancel={stopMove}
    >
      <div className="widget-dock-drag-bar">
        <div className="drag-handle-grip" title="Drag to move widget">
          <span>⣿</span>
          <span className="drag-label">{title.toUpperCase()}</span>
        </div>
        <div className="widget-dock-actions">
          <button
            type="button"
            className="dock-tool-btn dock-tool-btn--remove"
            onClick={() => onRemove(id)}
            title="Hide Widget"
          >
            ✕
          </button>
        </div>
      </div>
      <div className="widget-content-body">{children}</div>
    </div>
  );
}

export function RightWidgets() {
  const [activeTab, setActiveTab] = useState<WidgetCategory>("media");
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [enabledWidgets, setEnabledWidgets] = useState<WidgetId[]>(["music", "weather", "news", "lighting", "tasks"]);
  const [widgetPlacements, setWidgetPlacements] = useState<Record<string, WidgetPlacement>>(readLayout);
  const [lightIntensity, setLightIntensity] = useState(72);
  const [lightColor, setLightColor] = useState<"warm" | "emerald" | "neon" | "sunset" | "white">("warm");
  const [tasks, setTasks] = useState<TaskItem[]>([
    { id: "1", title: "AURA System Performance Optimization", time: "2:00 PM", completed: false, priority: "high" },
    { id: "2", title: "Local Knowledge Base Sync", time: "4:30 PM", completed: true, priority: "normal" },
    { id: "3", title: "Review daily AI summaries", time: "6:00 PM", completed: false, priority: "normal" },
  ]);
  const [newTaskInput, setNewTaskInput] = useState("");
  const [isAddingTask, setIsAddingTask] = useState(false);

  const categoryWidgets = useMemo(
    () => enabledWidgets.filter((id) => WIDGET_CATALOG.find((w) => w.id === id)?.category === activeTab),
    [activeTab, enabledWidgets],
  );

  const boardHeight = useMemo(
    () =>
      Math.max(
        760,
        ...categoryWidgets.map((id, index) => {
          const meta = WIDGET_CATALOG.find((w) => w.id === id);
          const size = floatingSize(meta?.name || "");
          const placement = widgetPlacements[id] || { ...defaultPlacement(index), ...size };
          return placement.y + placement.h + 40;
        }),
      ),
    [categoryWidgets, widgetPlacements],
  );

  useEffect(() => {
    saveLayout(widgetPlacements);
  }, [widgetPlacements]);

  function updatePlacement(id: WidgetId, next: WidgetPlacement) {
    setWidgetPlacements((current) => ({
      ...current,
      [id]: {
        x: Math.round(next.x),
        y: Math.round(next.y),
        w: Math.max(MIN_W, Math.round(next.w)),
        h: Math.max(MIN_H, Math.round(next.h)),
      },
    }));
  }

  function toggleWidgetEnabled(id: WidgetId) {
    setEnabledWidgets((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]));
  }

  function removeWidget(id: WidgetId) {
    setEnabledWidgets((prev) => prev.filter((item) => item !== id));
  }

  function resetLayout() {
    const next: Record<string, WidgetPlacement> = {};
    categoryWidgets.forEach((id, index) => {
      next[id] = defaultPlacement(index);
    });
    setWidgetPlacements(next);
  }

  function toggleTask(id: string) {
    setTasks((prev) => prev.map((task) => (task.id === id ? { ...task, completed: !task.completed } : task)));
  }

  function addTask(e: React.FormEvent) {
    e.preventDefault();
    const clean = newTaskInput.trim();
    if (!clean) return;
    setTasks((prev) => [
      { id: Date.now().toString(), title: clean, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), completed: false, priority: "normal" },
      ...prev,
    ]);
    setNewTaskInput("");
    setIsAddingTask(false);
  }

  function renderWidgetContent(id: WidgetId) {
    if (id === "music") return <MusicWidget />;
    if (id === "weather") return <WeatherWidget />;
    if (id === "events") return <TodayEventsWidget />;
    if (id === "year") return <YearProgressWidget />;
    if (id === "news") return <NewsWidget />;
    if (id === "companion") return <AuraCompanionWidget />;

    if (id === "lighting") {
      const glows: Record<string, string> = {
        warm: "radial-gradient(circle, rgba(251,191,36,0.45) 0%, rgba(245,158,11,0) 70%)",
        emerald: "radial-gradient(circle, rgba(16,185,129,0.45) 0%, rgba(5,150,105,0) 70%)",
        neon: "radial-gradient(circle, rgba(59,130,246,0.45) 0%, rgba(37,99,235,0) 70%)",
        sunset: "radial-gradient(circle, rgba(244,114,182,0.45) 0%, rgba(219,39,119,0) 70%)",
        white: "radial-gradient(circle, rgba(255,255,255,0.6) 0%, rgba(226,232,240,0) 70%)",
      };
      return (
        <section className="widget-panel-card smart-space-widget">
          <div className="smart-space-top">
            <span className="smart-space-category">Ambient Workspace Lighting</span>
            <span className="light-percentage-badge">{lightIntensity}%</span>
          </div>
          <h4 className="smart-space-title">Smart Glow</h4>
          <input type="range" min="0" max="100" value={lightIntensity} onChange={(e) => setLightIntensity(Number(e.target.value))} className="lighting-slider-input" />
          <div className="lighting-preset-pills">
            {(["warm", "emerald", "neon", "sunset", "white"] as const).map((c) => (
              <button key={c} type="button" className={`light-chip light-chip--${c} ${lightColor === c ? "active" : ""}`} onClick={() => setLightColor(c)}>
                {c}
              </button>
            ))}
          </div>
          <div className="smart-space-glow-canvas" style={{ opacity: 0.25 + lightIntensity / 130, background: glows[lightColor] }} />
        </section>
      );
    }

    if (id === "tasks") {
      const completedCount = tasks.filter((task) => task.completed).length;
      return (
        <section className="widget-panel-card tasks-widget">
          <header className="widget-panel-header">
            <div className="widget-title-group">
              <span className="widget-icon"><ChecklistIcon /></span>
              <div>
                <h3 className="widget-title">Tasks</h3>
                <span className="tasks-progress-subtitle">{completedCount} of {tasks.length} completed</span>
              </div>
            </div>
            <button className="widget-action-icon" type="button" onClick={() => setIsAddingTask((prev) => !prev)} title="Add task"><PlusIcon /></button>
          </header>
          {isAddingTask && (
            <form onSubmit={addTask} className="task-add-form">
              <input value={newTaskInput} onChange={(e) => setNewTaskInput(e.target.value)} placeholder="What needs to be done?" className="task-add-input" autoFocus />
              <button type="submit" className="task-add-submit-btn">Add</button>
            </form>
          )}
          <div className="tasks-list">
            {tasks.map((task) => (
              <div key={task.id} className={`task-row-item ${task.completed ? "task-row-item--done" : ""}`}>
                <label className="toggle-switch">
                  <input type="checkbox" checked={task.completed} onChange={() => toggleTask(task.id)} />
                  <span className="toggle-slider" />
                </label>
                <div className="task-info" onClick={() => toggleTask(task.id)}>
                  <span className="task-title">{task.title}</span>
                  <span className="task-time">{task.time}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    return null;
  }

  return (
    <aside className="right-widgets-column" aria-label="AURA Categorized Interactive Widgets">
      <div className="widget-category-tabs-bar">
        <div className="widget-category-tabs">
          <button type="button" className={`widget-tab-pill ${activeTab === "media" ? "active" : ""}`} onClick={() => setActiveTab("media")}>🎵 Music</button>
          <button type="button" className={`widget-tab-pill ${activeTab === "info" ? "active" : ""}`} onClick={() => setActiveTab("info")}>🌦️ Info</button>
          <button type="button" className={`widget-tab-pill ${activeTab === "space" ? "active" : ""}`} onClick={() => setActiveTab("space")}>💡 Space</button>
        </div>
        <button type="button" className={`widget-add-drawer-btn ${showAddMenu ? "active" : ""}`} onClick={() => setShowAddMenu((prev) => !prev)} title="Add / Manage Widgets">
          <span className="plus-symbol">＋</span>
          <span>Add</span>
        </button>
      </div>

      {showAddMenu && (
        <div className="widget-catalog-drawer">
          <div className="catalog-drawer-header">
            <span className="catalog-drawer-title">Widget Catalog</span>
            <button type="button" className="catalog-close-btn" onClick={() => setShowAddMenu(false)}>✕</button>
          </div>
          <div className="catalog-items-grid">
            {WIDGET_CATALOG.map((item) => {
              const isEnabled = enabledWidgets.includes(item.id);
              return (
                <div key={item.id} className="catalog-item-card">
                  <div className="catalog-item-icon">{item.icon}</div>
                  <div className="catalog-item-info">
                    <strong>{item.name}</strong>
                    <p>{item.description}</p>
                  </div>
                  <button type="button" className={`catalog-toggle-btn ${isEnabled ? "enabled" : ""}`} onClick={() => toggleWidgetEnabled(item.id)}>
                    {isEnabled ? "✓ Active" : "+ Add"}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="widget-cards-scroll-container widget-grid-freeform" style={{ minHeight: `${boardHeight}px` }}>
        <div className="multi-card-board-tools">
          <button type="button" className="widget-add-drawer-btn active" onClick={resetLayout}>Reset layout</button>
        </div>
        {categoryWidgets.length > 0 ? (
          categoryWidgets.map((id, index) => {
            const meta = WIDGET_CATALOG.find((w) => w.id === id);
            const placement = widgetPlacements[id] || { ...defaultPlacement(index), ...floatingSize(meta?.name || "") };
            return (
              <FloatingCard
                key={id}
                id={id}
                title={meta?.name || id}
                placement={placement}
                onMove={updatePlacement}
                onResize={updatePlacement}
                onRemove={removeWidget}
              >
                {renderWidgetContent(id)}
              </FloatingCard>
            );
          })
        ) : (
          <div className="empty-category-notice">
            <span>📭</span>
            <p>No widgets in this category.</p>
            <button type="button" className="empty-add-btn" onClick={() => setShowAddMenu(true)}>+ Add Widget</button>
          </div>
        )}
      </div>
    </aside>
  );
}
