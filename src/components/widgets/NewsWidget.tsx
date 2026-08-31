import { FormEvent, useEffect, useMemo, useState } from "react";
import { auraApi, NewsArticle } from "../../services/auraApi";

export interface EditorialNewsArticle {
  id: string;
  type: "hero-bleed" | "split-card" | "compact";
  author: string;
  date: string;
  title: string;
  excerpt: string;
  category: string;
  image?: string;
  url: string;
  fullContent?: string;
}

interface NewsWidgetProps {
  onViewMore?: () => void;
}

const CATEGORIES = ["All", "Culture", "Psychology", "Technology", "Neuroscience"];
const FALLBACK_IMAGES = [
  "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=900&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1495020689067-958852a7765e?q=80&w=900&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=900&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1532012197267-da84d127e765?q=80&w=900&auto=format&fit=crop",
];

function articleDate(article: NewsArticle): string {
  if (!article.published_at) return "Latest";
  const date = new Date(article.published_at);
  if (Number.isNaN(date.getTime())) return article.published_at;
  return date.toLocaleDateString(undefined, { day: "2-digit", month: "2-digit", year: "numeric" });
}

function queryForCategory(category: string): string {
  if (category === "Culture") return "culture arts";
  if (category === "Psychology") return "psychology mental health";
  if (category === "Neuroscience") return "neuroscience brain research";
  return "";
}

function toEditorialArticle(article: NewsArticle, index: number): EditorialNewsArticle {
  return {
    id: article.id || `${article.title}-${index}`,
    type: index === 0 ? "hero-bleed" : index === 1 ? "split-card" : "compact",
    author: article.source ? `By ${article.source}` : "By AURA News",
    date: articleDate(article),
    title: article.title,
    excerpt: article.excerpt || "Open the source for details.",
    category: article.category || "News",
    image: article.image_url || FALLBACK_IMAGES[index % FALLBACK_IMAGES.length],
    url: article.url,
    fullContent: article.excerpt || "Open the original source for the full story.",
  };
}

export function NewsWidget({ onViewMore }: NewsWidgetProps) {
  const [articles, setArticles] = useState<EditorialNewsArticle[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<EditorialNewsArticle | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadNews(category = activeCategory, query = searchQuery) {
    setLoading(true);
    setError("");
    try {
      const lookup = query.trim() || queryForCategory(category);
      const apiCategory = category === "Technology" ? "Technology" : "All";
      const response = await auraApi.getNews(apiCategory, lookup, 8);
      if (!response.ok) {
        throw new Error(response.error?.message || "News is unavailable.");
      }
      setArticles((response.data.articles || []).map(toEditorialArticle));
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
  const splitArticle = articles[1] || articles[0];
  const compactArticles = useMemo(() => articles.slice(2, 6), [articles]);

  return (
    <div className="editorial-news-suite" aria-label="Editorial News Gallery">
      <div className="editorial-news-header-row">
        <div className="news-suite-title-group">
          <span className="news-suite-glyph">News</span>
          <h2 className="news-suite-title">Editorial Insights</h2>
        </div>

        <div className="editorial-header-actions-group">
          <form className="editorial-news-search" onSubmit={submitSearch}>
            <input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Search current news..." />
            <button type="submit" disabled={loading}>{loading ? "Loading" : "Search"}</button>
          </form>
          <div className="editorial-category-pills" role="tablist">
            {CATEGORIES.map((cat) => (
              <button key={cat} type="button" className={`editorial-cat-chip ${activeCategory === cat ? "active" : ""}`} onClick={() => chooseCategory(cat)}>
                {cat}
              </button>
            ))}
          </div>

          {onViewMore && (
            <button type="button" className="news-view-more-nav-btn" onClick={onViewMore} title="Open Dedicated News Tab">
              View more
            </button>
          )}
        </div>
      </div>

      {error && <p className="news-live-error">{error}</p>}

      {!error && !heroArticle && (
        <div className="memory-empty-state">
          <h3 className="empty-state-title">{loading ? "Loading current news..." : "No headlines found"}</h3>
          <p className="empty-state-text">Try another category or search topic.</p>
        </div>
      )}

      {heroArticle && (
        <div className="editorial-news-triptych-grid">
          <article className="news-card-hero-bleed" onClick={() => setSelectedArticle(heroArticle)} title={`Read "${heroArticle.title}"`}>
            <div className="hero-bleed-image-layer" style={{ backgroundImage: `url(${heroArticle.image})` }} />
            <div className="hero-bleed-dark-scrim" />
            <div className="hero-bleed-content-box">
              <h3 className="hero-bleed-title">{heroArticle.title}</h3>
              <p className="hero-bleed-excerpt">{heroArticle.excerpt}</p>
              <div className="hero-bleed-bottom-bar">
                <button type="button" className="coral-read-more-btn" onClick={(event) => {
                  event.stopPropagation();
                  setSelectedArticle(heroArticle);
                }}>
                  Read more
                </button>
              </div>
            </div>
          </article>

          {splitArticle && (
            <article className="news-card-split" onClick={() => setSelectedArticle(splitArticle)} title={`Read "${splitArticle.title}"`}>
              <div className="split-card-photo" style={{ backgroundImage: `url(${splitArticle.image})` }} />
              <div className="split-card-content">
                <div className="split-card-meta-row">
                  <span className="split-author">{splitArticle.author}</span>
                  <span className="split-date">{splitArticle.date}</span>
                </div>
                <h3 className="split-card-title">{splitArticle.title}</h3>
                <p className="split-card-excerpt">{splitArticle.excerpt}</p>
                <div className="split-card-bottom-bar">
                  <button type="button" className="coral-read-more-btn" onClick={(event) => {
                    event.stopPropagation();
                    setSelectedArticle(splitArticle);
                  }}>
                    Read more
                  </button>
                </div>
              </div>
            </article>
          )}

          <div className="news-compact-stack">
            {compactArticles.map((article) => (
              <article key={article.id} className="news-card-compact" onClick={() => setSelectedArticle(article)} title={`Read "${article.title}"`}>
                <div className="compact-meta-row">
                  <span className="compact-author">{article.author}</span>
                  <span className="compact-date">{article.date}</span>
                </div>
                <h4 className="compact-title">{article.title}</h4>
                <p className="compact-excerpt">{article.excerpt}</p>
              </article>
            ))}
          </div>
        </div>
      )}

      {onViewMore && (
        <div className="news-suite-footer-bar">
          <button type="button" className="news-suite-view-all-btn" onClick={onViewMore}>
            <span>View all stories in Dedicated News Hub</span>
            <span className="view-arrow-icon">-&gt;</span>
          </button>
        </div>
      )}

      {selectedArticle && (
        <div className="news-reader-modal-backdrop" onClick={() => setSelectedArticle(null)} role="dialog" aria-modal="true">
          <div className="news-reader-modal-sheet" onClick={(event) => event.stopPropagation()}>
            <div className="reader-modal-header">
              <span className="reader-category-pill">{selectedArticle.category}</span>
              <button type="button" className="reader-close-btn" onClick={() => setSelectedArticle(null)} title="Close">
                Close
              </button>
            </div>

            {selectedArticle.image && <div className="reader-banner-image" style={{ backgroundImage: `url(${selectedArticle.image})` }} />}

            <div className="reader-article-body">
              <div className="reader-meta-line">
                <strong className="reader-author">{selectedArticle.author}</strong>
                <span>/</span>
                <span className="reader-date">{selectedArticle.date}</span>
              </div>
              <h2 className="reader-headline">{selectedArticle.title}</h2>
              <p className="reader-lead-paragraph">{selectedArticle.excerpt}</p>
              <p className="reader-full-text">{selectedArticle.fullContent}</p>
              <a className="coral-read-more-btn" href={selectedArticle.url} target="_blank" rel="noreferrer">
                Open source
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
