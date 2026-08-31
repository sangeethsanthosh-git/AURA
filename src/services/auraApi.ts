export type BackendState = "STARTING" | "READY" | "DEGRADED" | "OFFLINE" | "ERROR";

export interface AuraResponse {
  text: string;
  success: boolean;
  spoken_text?: string | null;
  intent: string;
  execution_source: string;
  llm_provider: string;
  model: string;
  execution_time: number;
  metadata: Record<string, unknown>;
  error?: string | null;
  raw?: Record<string, unknown>;
}

export interface ActivityRecord {
  user_message: string;
  response_text: string;
  intent: string;
  execution_source: string;
  llm_provider: string;
  model: string;
  execution_time: number;
  success: boolean;
  error?: string | null;
}

export interface MemoryRecord {
  id?: string;
  category: string;
  content: string;
  status: string;
  importance?: number;
  updated_at?: string;
}

export type ProviderStatus = Record<string, string>;

export interface VoiceProfile {
  id: string;
  display_name: string;
  engine: string;
  languages: string[];
  available: boolean;
  reason?: string | null;
}

export interface VoiceProfilesResponse {
  profiles: VoiceProfile[];
  active_style: string;
}

export interface WeatherCurrentResponse {
  ok: boolean;
  message?: string | null;
  data: {
    location?: {
      name?: string;
      state?: string;
      country?: string;
    };
    formatted_weather?: {
      temperature?: number;
      condition?: string;
      wind_speed?: number;
      humidity?: number;
      feels_like?: number;
      message?: string;
    };
  };
  error?: { message?: string } | null;
}

export interface WebSearchResult {
  title: string;
  url: string;
  domain: string;
  snippet?: string;
}

export interface WebSearchResponse {
  ok: boolean;
  query: string;
  results: WebSearchResult[];
}

export interface NewsArticle {
  id: string;
  title: string;
  excerpt: string;
  url: string;
  source: string;
  category: string;
  published_at: string;
  image_url?: string;
}

export interface NewsHeadlinesResponse {
  ok: boolean;
  message?: string | null;
  data: {
    category: string;
    query: string;
    articles: NewsArticle[];
    source: string;
    execution_time_seconds?: number;
  };
  error?: { message?: string } | null;
}

export interface SpotifyTrack {
  id?: string;
  title: string;
  artist: string;
  album?: string;
  imageUrl?: string;
  uri?: string;
  externalUrl?: string;
  durationMs?: number;
}

export interface SpotifyPlayback extends SpotifyTrack {
  ok: boolean;
  active?: boolean;
  needsAuth?: boolean;
  message?: string;
  isPlaying?: boolean;
  progressMs?: number;
  device?: string;
}

async function invoke<T>(command: string, payload?: unknown): Promise<T> {
  if (!window.aura) {
    throw new Error("AURA desktop bridge is not available.");
  }
  return window.aura.request<T>({ command: command as never, payload });
}

export const auraApi = {
  getStatus: () => invoke<{ backend: BackendState }>("status"),
  sendMessage: (message: string) => invoke<AuraResponse>("sendMessage", { message }),
  listMemories: () => invoke<MemoryRecord[]>("listMemories"),
  forgetMemory: (content: string) => invoke<AuraResponse>("forgetMemory", { content }),
  getActivities: () => invoke<ActivityRecord[]>("activities"),
  getProviderStatus: () => invoke<ProviderStatus>("providerStatus"),
  getVoiceState: () => invoke<{ state: string }>("voiceState"),
  getVoiceProfiles: () => invoke<VoiceProfilesResponse>("voiceProfiles"),
  speakText: (text: string, language = "en", voice?: string) => invoke<{ ok: boolean; engine: string; language: string; voice?: string | null }>("speakText", { text, language, voice }),
  startVoice: () => invoke<{ success: boolean; text?: string; error?: string }>("startVoice"),
  stopVoice: () => invoke<{ success: boolean; text?: string; error?: string }>("stopVoice"),
  getWeather: (location?: string) => invoke<WeatherCurrentResponse>("weatherCurrent", { location }),
  getNews: (category = "All", query = "", limit = 12) => invoke<NewsHeadlinesResponse>("newsHeadlines", { category, query, limit }),
  webSearch: (query: string, limit = 5) => invoke<WebSearchResponse>("webSearch", { query, limit }),
  loadProviderKeys: () => window.aura?.settings.loadProviderKeys() ?? Promise.resolve([]),
  saveProviderKeys: (keys: Array<{ id: string; provider: "groq" | "huggingface" | "nvidia"; label: string; value: string; status: "ready" | "limited" | "empty" }>) =>
    window.aura?.settings.saveProviderKeys(keys) ?? Promise.resolve({ ok: false }),
};

export const spotifyApi = {
  connect: () => window.aura?.spotify?.request<{ ok: boolean; message?: string }>("connect") ?? Promise.resolve({ ok: false, message: "Spotify bridge is unavailable." }),
  disconnect: () => window.aura?.spotify?.request<{ ok: boolean; message?: string }>("disconnect") ?? Promise.resolve({ ok: false, message: "Spotify bridge is unavailable." }),
  current: () => window.aura?.spotify?.request<SpotifyPlayback>("current") ?? Promise.resolve({ ok: false, needsAuth: true, title: "Spotify", artist: "", message: "Spotify bridge is unavailable." }),
  play: (uri?: string) => window.aura?.spotify?.request<{ ok: boolean; message?: string }>("play", { uri }) ?? Promise.resolve({ ok: false, message: "Spotify bridge is unavailable." }),
  pause: () => window.aura?.spotify?.request<{ ok: boolean; message?: string }>("pause") ?? Promise.resolve({ ok: false, message: "Spotify bridge is unavailable." }),
  playpause: () => window.aura?.spotify?.request<{ ok: boolean; message?: string }>("playpause") ?? Promise.resolve({ ok: false, message: "Spotify bridge is unavailable." }),
  next: () => window.aura?.spotify?.request<{ ok: boolean; message?: string }>("next") ?? Promise.resolve({ ok: false, message: "Spotify bridge is unavailable." }),
  previous: () => window.aura?.spotify?.request<{ ok: boolean; message?: string }>("previous") ?? Promise.resolve({ ok: false, message: "Spotify bridge is unavailable." }),
  seek: (positionMs: number) => window.aura?.spotify?.request<{ ok: boolean; message?: string }>("seek", { positionMs }) ?? Promise.resolve({ ok: false, message: "Spotify bridge is unavailable." }),
  volume: (volume: number) => window.aura?.spotify?.request<{ ok: boolean; message?: string }>("volume", { volume }) ?? Promise.resolve({ ok: false, message: "Spotify bridge is unavailable." }),
  search: (query: string) => window.aura?.spotify?.request<{ ok: boolean; needsAuth?: boolean; message?: string; results?: SpotifyTrack[] }>("search", { query }) ?? Promise.resolve({ ok: false, message: "Spotify bridge is unavailable.", results: [] }),
};

export interface YouTubeSearchResult {
  id: string;
  title: string;
  channel: string;
  thumbnail: string;
  duration?: string;
}

export const youtubeApi = {
  search: async (query: string): Promise<{ ok: boolean; results: YouTubeSearchResult[]; message?: string }> => {
    if (window.aura?.youtube?.search) {
      try {
        const res = await window.aura.youtube.search(query);
        if (res.ok && res.results && res.results.length > 0) {
          return { ok: true, results: res.results };
        }
      } catch {
        // Fallback
      }
    }

    const endpoints = [
      `https://pipedapi.kavin.rocks/search?q=${encodeURIComponent(query)}&filter=videos`,
      `https://api.piped.privacydev.net/search?q=${encodeURIComponent(query)}&filter=videos`,
      `https://invidious.privacydev.net/api/v1/search?q=${encodeURIComponent(query)}&type=video`,
      `https://yt.artemislena.eu/api/v1/search?q=${encodeURIComponent(query)}&type=video`,
    ];

    for (const url of endpoints) {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 2500);
        const res = await fetch(url, { signal: controller.signal });
        clearTimeout(timeout);
        const data = await res.json();
        const items = Array.isArray(data) ? data : data?.items || [];
        if (Array.isArray(items) && items.length > 0) {
          const results: YouTubeSearchResult[] = items
            .map((v: any) => {
              const id = v.videoId || v.id || (typeof v.url === "string" ? v.url.split("v=")[1] : "");
              if (!id) return null;
              return {
                id,
                title: v.title || "YouTube Video",
                channel: v.uploaderName || v.author || v.channel || "YouTube",
                thumbnail: v.thumbnail || v.thumbnailUrl || v.videoThumbnails?.[0]?.url || `https://i.ytimg.com/vi/${id}/hqdefault.jpg`,
                duration: v.duration
                  ? typeof v.duration === "number"
                    ? `${Math.floor(v.duration / 60)}:${String(v.duration % 60).padStart(2, "0")}`
                    : String(v.duration)
                  : undefined,
              };
            })
            .filter(Boolean) as YouTubeSearchResult[];
          if (results.length > 0) {
            return { ok: true, results };
          }
        }
      } catch {
        continue;
      }
    }

    return { ok: false, results: [], message: "No search results found. Restart the desktop app or paste a direct YouTube link." };
  },
  openMini: (videoId?: string, query?: string) => {
    if (window.aura?.youtube?.openMini) {
      return window.aura.youtube.openMini(videoId, query);
    }
    return window.aura?.media.openExternal(videoId ? `https://www.youtube.com/watch?v=${videoId}` : `https://www.youtube.com/results?search_query=${encodeURIComponent(query || "")}`) ?? Promise.resolve({ ok: false });
  },
};
