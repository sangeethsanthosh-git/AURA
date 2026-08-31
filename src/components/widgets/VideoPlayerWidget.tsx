import { FormEvent, useState } from "react";
import { VideoFileIcon } from "../ui/Icons";
import { YouTubeSearchResult, youtubeApi } from "../../services/auraApi";

type YouTubeVideo = {
  id: string;
  title: string;
  channel: string;
  embedUrl: string;
  watchUrl: string;
  thumbnailUrl: string;
  duration?: string;
};

const PRESET_VIDEOS: YouTubeVideo[] = [
  {
    id: "jfKfPfyJRdk",
    title: "Lofi Hip Hop Radio - Beats to Relax/Study to",
    channel: "☕ Lofi Beats",
    embedUrl: "https://www.youtube-nocookie.com/embed/jfKfPfyJRdk",
    watchUrl: "https://www.youtube.com/watch?v=jfKfPfyJRdk",
    thumbnailUrl: "https://i.ytimg.com/vi/jfKfPfyJRdk/hqdefault.jpg",
  },
  {
    id: "4xDzrJKXOOY",
    title: "Synthwave Radio - Chill synth / retro beats",
    channel: "⚡ Synthwave",
    embedUrl: "https://www.youtube-nocookie.com/embed/4xDzrJKXOOY",
    watchUrl: "https://www.youtube.com/watch?v=4xDzrJKXOOY",
    thumbnailUrl: "https://i.ytimg.com/vi/4xDzrJKXOOY/hqdefault.jpg",
  },
  {
    id: "5qap5aO4i9A",
    title: "Lofi Hip Hop Mix - Relaxing beats for studying",
    channel: "🎧 Chill Mix",
    embedUrl: "https://www.youtube-nocookie.com/embed/5qap5aO4i9A",
    watchUrl: "https://www.youtube.com/watch?v=5qap5aO4i9A",
    thumbnailUrl: "https://i.ytimg.com/vi/5qap5aO4i9A/hqdefault.jpg",
  },
  {
    id: "kJQP7kiw5Fk",
    title: "Luis Fonsi - Despacito ft. Daddy Yankee",
    channel: "🎵 Top Hits",
    embedUrl: "https://www.youtube-nocookie.com/embed/kJQP7kiw5Fk",
    watchUrl: "https://www.youtube.com/watch?v=kJQP7kiw5Fk",
    thumbnailUrl: "https://i.ytimg.com/vi/kJQP7kiw5Fk/hqdefault.jpg",
  },
  {
    id: "fJ9rUzIMcZQ",
    title: "Queen – Bohemian Rhapsody (Official Video)",
    channel: "👑 Classic Rock",
    embedUrl: "https://www.youtube-nocookie.com/embed/fJ9rUzIMcZQ",
    watchUrl: "https://www.youtube.com/watch?v=fJ9rUzIMcZQ",
    thumbnailUrl: "https://i.ytimg.com/vi/fJ9rUzIMcZQ/hqdefault.jpg",
  },
];

export function VideoPlayerWidget({ onPrompt }: { onPrompt?: (prompt: string) => void }) {
  const [currentVideo, setCurrentVideo] = useState<YouTubeVideo>(PRESET_VIDEOS[0]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<YouTubeSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [isPlaying, setIsPlaying] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  async function handleSearchOrLoad(event: FormEvent) {
    event.preventDefault();
    const clean = searchQuery.trim();
    if (!clean) return;

    // 1. Check if user pasted a direct YouTube URL
    const parsed = parseYouTube(clean);
    if (parsed) {
      setLoadError("");
      setCurrentVideo(parsed);
      setIsPlaying(true);
      setSearchResults([]);
      setSearchQuery("");
      return;
    }

    // 2. Otherwise perform live in-app YouTube Search
    setSearching(true);
    setLoadError("");
    try {
      const res = await youtubeApi.search(clean);
      if (res.ok && res.results.length > 0) {
        setSearchResults(res.results);
        playSearchResult(res.results[0]);
      } else {
        // Fallback to direct YouTube search playlist embed
        const fallbackVideo: YouTubeVideo = {
          id: `search_${encodeURIComponent(clean)}`,
          title: `YouTube: "${clean}"`,
          channel: "YouTube Search",
          embedUrl: `https://www.youtube-nocookie.com/embed?listType=search&list=${encodeURIComponent(clean)}`,
          watchUrl: `https://www.youtube.com/results?search_query=${encodeURIComponent(clean)}`,
          thumbnailUrl: `https://i.ytimg.com/vi/jfKfPfyJRdk/hqdefault.jpg`,
        };
        setCurrentVideo(fallbackVideo);
        setIsPlaying(true);
      }
    } catch {
      const fallbackVideo: YouTubeVideo = {
        id: `search_${encodeURIComponent(clean)}`,
        title: `YouTube: "${clean}"`,
        channel: "YouTube Search",
        embedUrl: `https://www.youtube-nocookie.com/embed?listType=search&list=${encodeURIComponent(clean)}`,
        watchUrl: `https://www.youtube.com/results?search_query=${encodeURIComponent(clean)}`,
        thumbnailUrl: `https://i.ytimg.com/vi/jfKfPfyJRdk/hqdefault.jpg`,
      };
      setCurrentVideo(fallbackVideo);
      setIsPlaying(true);
    } finally {
      setSearching(false);
    }
  }

  function playSearchResult(item: YouTubeSearchResult) {
    setCurrentVideo({
      id: item.id,
      title: item.title,
      channel: item.channel,
      embedUrl: `https://www.youtube-nocookie.com/embed/${item.id}`,
      watchUrl: `https://www.youtube.com/watch?v=${item.id}`,
      thumbnailUrl: item.thumbnail,
      duration: item.duration,
    });
    setIsPlaying(true);
    setSearchResults([]);
  }

  function selectPreset(preset: YouTubeVideo) {
    setCurrentVideo(preset);
    setIsPlaying(true);
    setLoadError("");
    setSearchResults([]);
  }

  function openPopoutMini() {
    void youtubeApi.openMini(currentVideo.id, searchQuery || currentVideo.title);
  }

  return (
    <section
      className={`widget-panel-card video-player-widget ${isExpanded ? "video-player-widget--expanded" : ""}`}
      aria-label="Mini YouTube Widget"
    >
      <header className="widget-panel-header">
        <div className="widget-title-group">
          <span className="mini-yt-badge">▶</span>
          <h3 className="widget-title">Mini YouTube</h3>
        </div>
        <div className="video-header-controls">
          <button
            type="button"
            className="video-ctrl-icon-btn"
            onClick={openPopoutMini}
            title="Pop-out Floating Mini YouTube Window"
          >
            🗗
          </button>
          <button
            type="button"
            className="video-ctrl-icon-btn"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? "Collapse View" : "Expand Full Theater Window"}
          >
            {isExpanded ? "⤓" : "⤢"}
          </button>
          <button
            type="button"
            className="video-ctrl-icon-btn"
            onClick={() => void window.aura?.media.openExternal(currentVideo.watchUrl)}
            title="Open in External Browser"
          >
            ↗
          </button>
        </div>
      </header>

      {/* Preset Quick Channel Chips */}
      <div className="youtube-preset-chips">
        {PRESET_VIDEOS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            className={`preset-chip ${currentVideo.id === preset.id ? "active" : ""}`}
            onClick={() => selectPreset(preset)}
            title={preset.title}
          >
            {preset.channel}
          </button>
        ))}
      </div>

      {/* In-App Mini Video Screen */}
      <div className="video-display-area">
        {isPlaying ? (
          <iframe
            src={`${currentVideo.embedUrl}?autoplay=1&enablejsapi=1&rel=0&modestbranding=1&origin=${encodeURIComponent(typeof window !== "undefined" ? window.location.origin : "http://localhost")}`}
            title={currentVideo.title}
            className="video-iframe"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        ) : (
          <div className="video-thumbnail-container" onClick={() => setIsPlaying(true)}>
            <img
              src={currentVideo.thumbnailUrl}
              alt={currentVideo.title}
              className="video-thumb-img"
              onError={(e) => {
                (e.currentTarget as HTMLElement).style.display = "none";
              }}
            />
            <div className="video-play-overlay">
              <button
                type="button"
                className="video-center-play-btn"
                title="Play Video"
                onClick={() => setIsPlaying(true)}
              >
                ▶
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Video Meta Info */}
      <div className="video-info-meta">
        <h4 className="video-title" title={currentVideo.title}>{currentVideo.title}</h4>
        <div className="video-channel-row">
          <span className="video-channel-sub">
            {currentVideo.channel} {currentVideo.duration ? `• ${currentVideo.duration}` : ""}
          </span>
          <button
            type="button"
            className="mini-yt-popout-link"
            onClick={openPopoutMini}
            title="Open in Mini Window"
          >
            Popout Mini Player 🗗
          </button>
        </div>
      </div>

      {/* Universal Search & Link Input Form */}
      <form onSubmit={handleSearchOrLoad} className="video-url-input-form">
        <input
          type="text"
          placeholder="Search YouTube or paste video link..."
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          className="video-url-input"
        />
        <button type="submit" className="video-url-submit" disabled={searching}>
          {searching ? "..." : "Search"}
        </button>
      </form>
      {loadError && <span className="widget-error-note">{loadError}</span>}

      {/* In-App YouTube Search Results Feed */}
      {searchResults.length > 0 && (
        <div className="youtube-search-results-tray">
          <div className="youtube-results-header">
            <span>Results for "{searchQuery}"</span>
            <button type="button" className="youtube-results-close-btn" onClick={() => setSearchResults([])}>
              ✕
            </button>
          </div>
          <div className="youtube-results-scroll">
            {searchResults.map((item) => (
              <button
                key={item.id}
                type="button"
                className="youtube-result-card"
                onClick={() => playSearchResult(item)}
                title={item.title}
              >
                <div className="yt-result-thumb-wrapper">
                  <img src={item.thumbnail} alt="" className="yt-result-thumb" />
                  {item.duration && <span className="yt-result-duration">{item.duration}</span>}
                </div>
                <div className="yt-result-text">
                  <strong className="yt-result-title">{item.title}</strong>
                  <span className="yt-result-channel">{item.channel}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function parseYouTube(url: string): YouTubeVideo | null {
  try {
    const parsed = new URL(url);
    let id = "";
    if (parsed.hostname.includes("youtube.com")) {
      if (parsed.pathname === "/watch") {
        id = parsed.searchParams.get("v") || "";
      } else if (parsed.pathname.startsWith("/shorts/") || parsed.pathname.startsWith("/embed/")) {
        id = parsed.pathname.split("/")[2] || "";
      }
    }
    if (parsed.hostname === "youtu.be") {
      id = parsed.pathname.slice(1);
    }
    id = id.split("?")[0].split("&")[0];
    if (!/^[a-zA-Z0-9_-]{6,}$/.test(id)) {
      return null;
    }
    return {
      id,
      title: "YouTube Video",
      channel: "YouTube",
      embedUrl: `https://www.youtube-nocookie.com/embed/${id}`,
      watchUrl: `https://www.youtube.com/watch?v=${id}`,
      thumbnailUrl: `https://i.ytimg.com/vi/${id}/hqdefault.jpg`,
    };
  } catch {
    return null;
  }
}
