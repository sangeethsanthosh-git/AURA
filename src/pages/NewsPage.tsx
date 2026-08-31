import { FormEvent, useEffect, useMemo, useState } from "react";
import { auraApi, NewsArticle } from "../services/auraApi";

const CATEGORIES = ["All", "General", "World", "Technology"];

function articleDate(article: NewsArticle): string {
  if (!article.published_at) return "Latest";
  const date = new Date(article.published_at);
  if (Number.isNaN(date.getTime())) return article.published_at;
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function NewsPage() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<NewsArticle | null>(null);
  const [activeCategory, setActiveCategory] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  async function loadNews(category = activeCategory, query = searchQuery) {
    setLoading(true);
    setError("");
    try {
      const response = await auraApi.getNews(category, query.trim(), 14);
      if (!response.ok) {
        throw new Error(response.error?.message || "News is unavailable.");
      }
      setArticles(response.data.articles || []);
      setLastUpdated(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "News is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadNews("All", "");
  }, []);

  function chooseCategory(category: string) {
    setActiveCategory(category);
    setSearchQuery("");
    void loadNews(category, "");
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    void loadNews(activeCategory, searchQuery);
  }

  const heroArticle = articles[0];
  const standardArticles = useMemo(() => articles.slice(1), [articles]);

  return (
    <div className="dedicated-news-page-container" aria-label="Live News Hub">
      <header className="news-page-masthead">
        <div className="masthead-headline-group">
          <div className="masthead-tagline">
            <span className="masthead-dot" />
            <span>Live public RSS feeds / updated daily</span>
          </div>
          <h1 className="masthead-main-title">AURA Live News</h1>
          <p className="masthead-sub-title">
            Current headlines across world, general, and technology news. Sources open in your browser and are not stored as personal memory.
          </p>
        </div>

        <form className="news-page-controls-strip" onSubmit={submitSearch}>
          <div className="news-search-box">
            <span className="search-glyph">Search</span>
            <input
              type="text"
              className="news-search-input"
              placeholder="Search today's news..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
            {searchQuery && (
              <button type="button" className="search-clear-btn" onClick={() => setSearchQuery("")}>
                Clear
              </button>
            )}
          </div>

          <div className="news-filter-pills" role="tablist">
            {CATEGORIES.map((category) => (
              <button
                key={category}
                type="button"
                className={`news-page-cat-btn ${activeCategory === category ? "active" : ""}`}
                onClick={() => chooseCategory(category)}
              >
                {category}
              </button>
            ))}
            <button type="submit" className="news-page-cat-btn" disabled={loading}>
              {loading ? "Loading" : "Refresh"}
            </button>
          </div>
        </form>
      </header>

      <section className="news-page-featured-section" aria-label="Current Headlines">
        <div className="section-label-row">
          <h2 className="section-title">Current Headlines</h2>
          <span className="section-counter">{lastUpdated ? `Updated ${lastUpdated}` : `${articles.length} stories`}</span>
        </div>

        {error && <p className="news-live-error">{error}</p>}

        {!error && articles.length === 0 && (
          <div className="memory-empty-state">
            <h3 className="empty-state-title">{loading ? "Loading headlines..." : "No headlines found"}</h3>
            <p className="empty-state-text">Try another category or search topic.</p>
          </div>
        )}

        {heroArticle && (
          <div className="news-page-grid-layout">
            <article className="news-page-hero-card news-page-hero-card--live" onClick={() => setSelectedArticle(heroArticle)}>
              {heroArticle.image_url && <div className="news-page-card-image-layer" style={{ backgroundImage: `url(${heroArticle.image_url})` }} />}
              <div className="hero-card-scrim" />
              <div className="hero-card-content">
                <div className="hero-card-meta">
                  <span className="hero-cat-pill">{heroArticle.category}</span>
                  <span className="hero-read-time">{heroArticle.source}</span>
                </div>
                <h3 className="hero-card-title">{heroArticle.title}</h3>
                <p className="hero-card-excerpt">{heroArticle.excerpt}</p>
                <div className="hero-card-footer">
                  <span className="hero-author-text">{articleDate(heroArticle)}</span>
                  <button type="button" className="coral-read-more-btn" onClick={(event) => {
                    event.stopPropagation();
                    setSelectedArticle(heroArticle);
                  }}>
                    Read source
                  </button>
                </div>
              </div>
            </article>

            {standardArticles.map((article) => (
              <article key={article.id} className="news-page-standard-card" onClick={() => setSelectedArticle(article)}>
                {article.image_url && <div className="news-page-standard-image" style={{ backgroundImage: `url(${article.image_url})` }} />}
                <div className="card-body-content">
                  <div className="card-meta-row">
                    <span className="card-author-name">{article.source}</span>
                    <span className="card-date-label">{articleDate(article)}</span>
                  </div>
                  <h3 className="card-headline-title">{article.title}</h3>
                  <p className="card-excerpt-text">{article.excerpt}</p>
                  <div className="card-bottom-action-row">
                    <span className="card-read-time-pill">{article.category}</span>
                    <button type="button" className="coral-read-more-btn" onClick={(event) => {
                      event.stopPropagation();
                      setSelectedArticle(article);
                    }}>
                      Read source
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {selectedArticle && (
        <div className="news-reader-modal-backdrop" onClick={() => setSelectedArticle(null)} role="dialog" aria-modal="true">
          <div className="news-reader-modal-sheet" onClick={(event) => event.stopPropagation()}>
            <div className="reader-modal-header">
              <div className="reader-badge-cluster">
                <span className="reader-category-pill">{selectedArticle.category}</span>
                <span className="reader-readtime-tag">{selectedArticle.source}</span>
              </div>
              <button type="button" className="reader-close-btn" onClick={() => setSelectedArticle(null)} title="Close">
                Close
              </button>
            </div>
            {selectedArticle.image_url && <div className="reader-banner-image" style={{ backgroundImage: `url(${selectedArticle.image_url})` }} />}
            <div className="reader-article-body">
              <div className="reader-meta-line">
                <strong className="reader-author">{selectedArticle.source}</strong>
                <span>/</span>
                <span className="reader-date">{articleDate(selectedArticle)}</span>
              </div>
              <h2 className="reader-headline">{selectedArticle.title}</h2>
              <p className="reader-lead-paragraph">{selectedArticle.excerpt}</p>
              <a className="coral-read-more-btn" href={selectedArticle.url} target="_blank" rel="noreferrer">
                Open original article
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
