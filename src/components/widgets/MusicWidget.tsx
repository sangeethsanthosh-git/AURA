import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { SpotifyPlayback, SpotifyTrack, spotifyApi } from "../../services/auraApi";

type AudioTrack = {
  id: string;
  title: string;
  filePath: string;
  url: string;
};

export function MusicWidget() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [source, setSource] = useState<"spotify" | "local">("spotify");
  const [localPlaying, setLocalPlaying] = useState(false);
  const [tracks, setTracks] = useState<AudioTrack[]>([]);
  const [trackIndex, setTrackIndex] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(72);
  const [spotify, setSpotify] = useState<SpotifyPlayback | null>(null);
  const [spotifyResults, setSpotifyResults] = useState<SpotifyTrack[]>([]);
  const [spotifyQuery, setSpotifyQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const activeTrack = tracks[trackIndex];
  const spotifyMode = source === "spotify";
  const isPlaying = spotifyMode ? Boolean(spotify?.isPlaying) : localPlaying;
  const position = spotifyMode ? spotify?.progressMs || 0 : currentTime * 1000;
  const total = spotifyMode ? spotify?.durationMs || 0 : duration * 1000;
  const progress = total > 0 ? Math.min(100, (position / total) * 100) : 0;

  const display = useMemo(() => {
    if (spotifyMode) {
      const isSessionActive = spotify?.active && spotify?.title;
      return {
        title: isSessionActive ? spotify.title : "Spotify Desktop",
        artist: isSessionActive ? spotify.artist : "No media playing",
        detail: isSessionActive ? spotify.album || "Active Spotify playback" : "Open Spotify and play any song",
        imageUrl: spotify?.imageUrl,
      };
    }
    return {
      title: activeTrack?.title || "Local Audio",
      artist: activeTrack ? (localPlaying ? "Playing" : "Paused") : "Choose a local file",
      detail: activeTrack?.filePath || "MP3, WAV, OGG, FLAC, M4A, AAC",
      imageUrl: "",
    };
  }, [activeTrack, localPlaying, spotify, spotifyMode]);

  // Poll the desktop media session every 2 seconds in Spotify mode.
  useEffect(() => {
    if (source !== "spotify") {
      return;
    }
    void refreshSpotify(false);
    const interval = window.setInterval(() => void refreshSpotify(false), 2000);
    return () => window.clearInterval(interval);
  }, [source]);

  // Local progress ticker for smooth playback timeline
  useEffect(() => {
    if (!spotifyMode || !spotify?.isPlaying) {
      return;
    }
    const ticker = window.setInterval(() => {
      setSpotify((prev) => {
        if (!prev || !prev.isPlaying) return prev;
        const nextMs = (prev.progressMs || 0) + 1000;
        if (prev.durationMs && nextMs > prev.durationMs) return prev;
        return { ...prev, progressMs: nextMs };
      });
    }, 1000);
    return () => window.clearInterval(ticker);
  }, [spotifyMode, spotify?.isPlaying]);

  useEffect(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.volume = volume / 100;
    }
  }, [volume]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !activeTrack) {
      return;
    }
    audio.load();
    setCurrentTime(0);
    setDuration(0);
    if (localPlaying) {
      void audio.play().catch(() => setError("Audio playback was blocked."));
    }
  }, [activeTrack?.id]);

  async function refreshSpotify(showBusy = true) {
    if (showBusy) {
      setBusy(true);
    }
    setError("");
    try {
      const state = await spotifyApi.current();
      setSpotify(state);
    } catch (spotifyError) {
      setError(spotifyError instanceof Error ? spotifyError.message : "Media session unavailable.");
    } finally {
      if (showBusy) {
        setBusy(false);
      }
    }
  }

  async function handleMediaControl(action: "playpause" | "next" | "previous") {
    if (spotifyMode) {
      setBusy(true);
      try {
        if (action === "playpause") {
          await spotifyApi.playpause();
        } else if (action === "next") {
          await spotifyApi.next();
        } else if (action === "previous") {
          await spotifyApi.previous();
        }
        setTimeout(() => void refreshSpotify(false), 500);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Media key action failed.");
      } finally {
        setBusy(false);
      }
    }
  }

  async function searchSpotify(event: FormEvent) {
    event.preventDefault();
    const clean = spotifyQuery.trim();
    if (!clean) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await spotifyApi.search(clean);
      if (!result.ok) {
        setError(result.message || "Spotify search failed.");
        return;
      }
      setSpotifyResults(result.results || []);
    } finally {
      setBusy(false);
    }
  }

  async function selectLocalAudio() {
    setSource("local");
    setError("");
    const selected = await window.aura?.media.selectAudioFiles();
    if (selected?.length) {
      setTracks(selected);
      setTrackIndex(0);
      setLocalPlaying(false);
    }
  }

  async function toggleLocalPlayback() {
    if (!activeTrack) {
      await selectLocalAudio();
      return;
    }
    const audio = audioRef.current;
    if (!audio) {
      return;
    }
    if (localPlaying) {
      audio.pause();
      setLocalPlaying(false);
      return;
    }
    await audio.play();
    setLocalPlaying(true);
  }

  function moveLocalTrack(direction: -1 | 1) {
    if (!tracks.length) {
      return;
    }
    setTrackIndex((current) => (current + direction + tracks.length) % tracks.length);
  }

  function seekLocal(event: React.MouseEvent<HTMLDivElement>) {
    if (spotifyMode || !audioRef.current || !duration) {
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    const nextTime = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)) * duration;
    audioRef.current.currentTime = nextTime;
    setCurrentTime(nextTime);
  }

  async function openSpotifyTarget(target?: string) {
    await window.aura?.media.openExternal(toSpotifyDeepLink(target || spotify?.uri) || spotify?.externalUrl || "spotify:");
  }

  return (
    <section className={`widget-panel-card music-widget ${display.imageUrl ? "music-widget--has-banner" : "music-widget--media-active"}`} aria-label="Music widget">
      {display.imageUrl && (
        <div
          className="music-widget-backdrop"
          style={{ backgroundImage: `url(${display.imageUrl})` }}
          aria-hidden="true"
        />
      )}
      <div className="music-widget-overlay" aria-hidden="true" />
      {spotify?.active && display.title && (
        <div className="music-playing-banner" aria-hidden="true">
          <span className="music-playing-banner-note">♪</span>
          <span>{display.title}</span>
        </div>
      )}
      <audio
        ref={audioRef}
        src={activeTrack?.url}
        onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
        onLoadedMetadata={(event) => setDuration(Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : 0)}
        onEnded={() => moveLocalTrack(1)}
      />

      <header className="widget-panel-header">
        <div className="widget-title-group">
          <span className="widget-icon">♪</span>
          <h3 className="widget-title">Now Playing</h3>
        </div>
        <div className="music-source-toggle">
          <button
            type="button"
            className={`source-badge ${source === "spotify" ? "active" : ""}`}
            onClick={() => setSource("spotify")}
            title="Spotify Desktop playback"
          >
            Windows Media
          </button>
          <button
            type="button"
            className={`source-badge ${source === "local" ? "active" : ""}`}
            onClick={() => setSource("local")}
            title="Local Audio Files"
          >
            Local
          </button>
        </div>
      </header>

      <div className="music-body">
        <button
          type="button"
          className={`album-art-wrapper album-art-wrapper--generated ${isPlaying ? "playing" : ""}`}
          onClick={spotifyMode ? () => void refreshSpotify(true) : selectLocalAudio}
          title={spotifyMode ? "Refresh Windows media playback" : "Choose local audio files"}
        >
          {display.imageUrl ? (
            <img src={display.imageUrl} alt="" className="album-cover-img" />
          ) : (
            <span className="album-note">{display.title.slice(0, 1).toUpperCase()}</span>
          )}
          <div className="vinyl-groove-indicator" />
        </button>

        <div className="music-track-meta">
          <h4 className="track-title" title={display.title}>{display.title}</h4>
          <span className="track-artist" title={display.artist}>{display.artist}</span>
          <span className="track-album" title={display.detail}>{display.detail}</span>
        </div>
      </div>

      <div className="music-timeline">
        <span className="time-stamp">{formatMs(position)}</span>
        <div className={`progress-track ${spotifyMode ? "progress-track--readonly" : ""}`} onClick={seekLocal}>
          <div className="progress-fill" style={{ width: `${progress}%` }} />
          <div className="progress-handle" style={{ left: `${progress}%` }} />
        </div>
        <span className="time-stamp">{formatMs(total)}</span>
      </div>

      {spotifyMode ? (
        <div className="music-controls-row">
          <button
            type="button"
            className="music-ctrl-btn"
            title="Previous (System Media Key)"
            disabled={busy}
            onClick={() => void handleMediaControl("previous")}
          >
            {"⏮"}
          </button>
          <button
            type="button"
            className="music-play-btn"
            title={isPlaying ? "Pause (System Media Key)" : "Play (System Media Key)"}
            disabled={busy}
            onClick={() => void handleMediaControl("playpause")}
          >
            {isPlaying ? "⏸" : "▶"}
          </button>
          <button
            type="button"
            className="music-ctrl-btn"
            title="Next (System Media Key)"
            disabled={busy}
            onClick={() => void handleMediaControl("next")}
          >
            {"⏭"}
          </button>
          <button
            type="button"
            className="widget-command-button"
            onClick={() => void openSpotifyTarget()}
            title="Open Spotify Desktop App"
          >
            Open Spotify
          </button>
        </div>
      ) : (
        <div className="music-controls-row">
          <button type="button" className="music-ctrl-btn" title="Previous" onClick={() => moveLocalTrack(-1)}>{"⏮"}</button>
          <button type="button" className="music-play-btn" title={localPlaying ? "Pause" : "Play"} onClick={toggleLocalPlayback}>{localPlaying ? "⏸" : "▶"}</button>
          <button type="button" className="music-ctrl-btn" title="Next" onClick={() => moveLocalTrack(1)}>{"⏭"}</button>
          <div className="volume-slider-group" title={`Volume: ${volume}%`}>
            <span className="vol-icon">🔊</span>
            <input type="range" min="0" max="100" value={volume} onChange={(event) => setVolume(Number(event.target.value))} className="volume-range" />
          </div>
        </div>
      )}

      {!spotifyMode && (
        <button type="button" className="widget-command-button" onClick={selectLocalAudio}>Choose Local Audio</button>
      )}

      {error && <span className="widget-error-note">{error}</span>}
    </section>
  );
}

function formatMs(milliseconds: number) {
  if (!Number.isFinite(milliseconds) || milliseconds <= 0) {
    return "0:00";
  }
  const totalSeconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function toSpotifyDeepLink(target?: string) {
  if (!target) {
    return "";
  }
  if (target.startsWith("spotify:")) {
    return target;
  }
  try {
    const url = new URL(target);
    if (url.hostname.includes("open.spotify.com")) {
      const [, type, id] = url.pathname.split("/");
      if (type && id) {
        return `spotify:${type}:${id}`;
      }
    }
  } catch {
    return "";
  }
  return "";
}
