import { useState } from "react";
import { SearchIcon } from "../ui/Icons";

export function GoogleSearchWidget({
  onSearchToChat,
}: {
  onSearchToChat?: (query: string) => void;
}) {
  const [searchQuery, setSearchQuery] = useState("");

  function handleGoogleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const clean = searchQuery.trim();
    if (!clean) return;

    if (onSearchToChat) {
      onSearchToChat(`/groq search the web for ${clean}`);
    } else {
      window.open(`https://www.google.com/search?q=${encodeURIComponent(clean)}`, "_blank");
    }
    setSearchQuery("");
  }

  const trendingSearches = [
    "ASUS ROG AI optimizations",
    "Local Ollama models 2026",
    "Piper TTS Malayalam voices",
  ];

  return (
    <section className="widget-panel-card google-search-widget" aria-label="Google Search Widget">
      <header className="widget-panel-header">
        <div className="widget-title-group">
          <span className="widget-icon">🌐</span>
          <h3 className="widget-title">Google Web Search</h3>
        </div>
      </header>

      <form onSubmit={handleGoogleSubmit} className="google-search-bar">
        <span className="google-g-icon">G</span>
        <input
          type="text"
          className="google-search-input"
          placeholder="Search Google or ask web..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <button type="submit" className="google-search-btn" title="Search">
          <SearchIcon />
        </button>
      </form>

      <div className="trending-tags-row">
        <span className="trending-label">Trending:</span>
        {trendingSearches.map((tag, i) => (
          <button
            key={i}
            type="button"
            className="trending-chip"
            onClick={() => onSearchToChat?.(`/groq ${tag}`)}
          >
            {tag}
          </button>
        ))}
      </div>
    </section>
  );
}

