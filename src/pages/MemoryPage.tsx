import { FormEvent, useMemo, useState } from "react";
import { auraApi, MemoryRecord } from "../services/auraApi";
import { useAuraRuntime } from "../state/AuraContext";

const PAGE_SIZE = 4;

function formatMemoryDate(memory: MemoryRecord): string {
  if (!memory.updated_at) return "Local memory";
  const date = new Date(memory.updated_at);
  if (Number.isNaN(date.getTime())) return "Local memory";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function categoryLabel(memory: MemoryRecord): string {
  return String(memory.category || "Memory").replace(/_/g, " ").toLowerCase();
}

export function MemoryPage() {
  const { memories, refreshRuntime } = useAuraRuntime();
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Write a memory into AURA's local book.");

  const filtered = useMemo(() => {
    const clean = query.trim().toLowerCase();
    if (!clean) return memories;
    return memories.filter((memory) => {
      const searchable = `${memory.category} ${memory.content} ${memory.status}`.toLowerCase();
      return searchable.includes(clean);
    });
  }, [memories, query]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const visibleMemories = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);
  const featuredMemory = visibleMemories[0] || filtered[0];

  async function saveMemory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const clean = draft.trim();
    if (!clean || busy) return;

    setBusy(true);
    setMessage("Writing to local memory...");
    try {
      const response = await auraApi.sendMessage(`Remember ${clean}`);
      await refreshRuntime();
      setDraft("");
      setPage(0);
      setMessage(response.text || "Saved to AURA's memory book.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Memory save failed.");
    } finally {
      setBusy(false);
    }
  }

  async function forgetMemory(memory: MemoryRecord) {
    if (busy) return;
    setBusy(true);
    setMessage("Removing memory...");
    try {
      const response = await auraApi.forgetMemory(memory.content);
      await refreshRuntime();
      setMessage(response.text || "Memory removed.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Forget request failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="memory-book-world" aria-label="AURA Memory">
      <div className="memory-book-topbar">
        <div className="memory-icon-cluster" aria-hidden="true">
          <button type="button">M</button>
          <button type="button">A</button>
        </div>
        <div className="memory-book-title">
          <span>{filtered.length} pages</span>
          <h1>AURA's memory</h1>
          <p className="memory-kicker">{message}</p>
        </div>
        <label className="memory-search-pill">
          <span>Search</span>
          <input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(0);
            }}
            placeholder="Find a memory"
          />
        </label>
      </div>

      <div className="memory-book-stage">
        <div className="memory-book-shadow" />
        <div className="memory-book-page memory-book-page-left">
          <div className="memory-page-grid">
            <form className="memory-ink-form" onSubmit={saveMemory}>
              <h2>Write into the book</h2>
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Remember that I prefer quiet focused work in the morning."
                rows={6}
              />
              <div className="memory-form-actions">
                <span>{draft.trim().length}/2000</span>
                <button type="submit" disabled={!draft.trim() || busy}>
                  {busy ? "Saving" : "Save memory"}
                </button>
              </div>
            </form>

            <article className="memory-feature-note">
              <small>Featured page</small>
              {featuredMemory ? (
                <>
                  <span>{categoryLabel(featuredMemory)}</span>
                  <strong>{featuredMemory.content}</strong>
                  <p>{formatMemoryDate(featuredMemory)}</p>
                </>
              ) : (
                <>
                  <span>empty</span>
                  <strong>No active long-term memory yet.</strong>
                  <p>Saved memories stay local and flow through the MemoryManager.</p>
                </>
              )}
            </article>
          </div>
        </div>

        <div className="memory-book-page memory-book-page-right">
          <div className="memory-page-list">
            {visibleMemories.length === 0 ? (
              <article className="memory-note-card empty">
                <div className="memory-note-body">
                  <span className="memory-note-dot" />
                  <div>
                    <strong>{query ? "No matching memory" : "The book is blank"}</strong>
                    <p>{query ? "Try a different search." : "Add a memory from the left page."}</p>
                    <small>Local memory</small>
                  </div>
                </div>
              </article>
            ) : (
              visibleMemories.map((memory, index) => (
                <article className={`memory-note-card ${index === 0 ? "active" : ""}`} key={memory.id || memory.content}>
                  <div className="memory-note-body">
                    <span className="memory-note-dot" />
                    <div>
                      <strong>{memory.content}</strong>
                      <p>{categoryLabel(memory)} / {memory.status || "ACTIVE"}</p>
                      <small>{formatMemoryDate(memory)}</small>
                    </div>
                  </div>
                  <button className="memory-forget-btn" type="button" onClick={() => forgetMemory(memory)} disabled={busy}>
                    Forget
                  </button>
                </article>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="memory-book-controls">
        <button type="button" onClick={() => setPage((value) => Math.max(0, value - 1))} disabled={safePage === 0}>
          Prev
        </button>
        <button type="button" aria-label="Refresh memories" onClick={() => void refreshRuntime()} disabled={busy}>
          Refresh
        </button>
        <button type="button" onClick={() => setPage((value) => Math.min(pageCount - 1, value + 1))} disabled={safePage >= pageCount - 1}>
          Next
        </button>
      </div>
    </section>
  );
}
