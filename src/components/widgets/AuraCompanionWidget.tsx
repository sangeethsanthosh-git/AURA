import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { auraApi, MemoryRecord, NewsArticle, SpotifyPlayback, spotifyApi, VoiceProfile, WeatherCurrentResponse, youtubeApi } from "../../services/auraApi";
import { readAppSettings, subscribeToAppSettings } from "../../state/appSettings";

type Mood = "calm" | "happy" | "thinking" | "speaking" | "listening" | "sleepy" | "weather" | "news" | "music" | "surprised" | "laugh";
type CalendarTone = "green" | "neutral" | "amber" | "blue" | "pink";

interface CompanionCalendarEvent {
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

interface CompanionReminderPrefs {
  email: string;
  phone: string;
}

interface CompanionReminderItem {
  id: string;
  title: string;
  time: string;
  note: string;
  date: string;
}

const COMPANION_MODELS = [
  { label: "gemma3:1b", value: "gemma3:1b" },
  { label: "llama3.2:3b", value: "llama3.2:3b" },
  { label: "qwen3:4b", value: "qwen3:4b" },
  { label: "gemma3:4b", value: "gemma3:4b" },
];

const MOOD_COPY: Record<Mood, string> = {
  calm: "I am here with you. Ask anything.",
  happy: "That sounds good. I am ready.",
  thinking: "Let me think through it carefully.",
  speaking: "I will say this out loud.",
  listening: "Say hey AURA, then tell me what to do.",
  sleepy: "Quiet mode. I will keep it soft.",
  weather: "Checking the sky for you.",
  news: "Opening today's headlines.",
  music: "Listening to the beat.",
  surprised: "Something interesting just landed.",
  laugh: "That gave me a little spark.",
};

function locationFromPrompt(text: string) {
  const match = text.match(/\b(?:in|at|for)\s+([a-zA-Z\s,.-]{2,})$/i);
  return match?.[1]?.trim() || "";
}

function isWeatherPrompt(text: string) {
  return /\b(weather|temperature|rain|forecast|humidity)\b/i.test(text);
}

function isNewsPrompt(text: string) {
  return /\b(news|headlines|latest|today's news|newspaper)\b/i.test(text);
}

function mediaAction(text: string): "playpause" | "next" | "previous" | "current" | "" {
  if (/\b(next|skip)\b/i.test(text)) return "next";
  if (/\b(previous|back|last song)\b/i.test(text)) return "previous";
  if (/\b(play|pause|resume|stop music|music)\b/i.test(text)) return "playpause";
  if (/\b(what is playing|now playing|current song)\b/i.test(text)) return "current";
  return "";
}

function isSearchPrompt(text: string) {
  return /^(search|google|web search|find online)\b/i.test(text) || /\b(search google|google search)\b/i.test(text);
}

function cleanSearchQuery(text: string) {
  return text.replace(/^(search|google|web search|find online)\s+/i, "").replace(/\b(search google|google search)\b/i, "").trim();
}

function isOpenAppPrompt(text: string) {
  return /^open\s+(app\s+)?[a-z0-9 ._-]+$/i.test(text) && !/\.[a-z0-9]{1,8}$/i.test(text);
}

function parseOpenAndSearch(text: string) {
  const match = text.match(/^open\s+(.+?)\s+and\s+(search|google|find|play)\s+(.+)$/i);
  if (!match) return null;
  return {
    app: match[1].trim(),
    action: match[2].toLowerCase(),
    query: match[3].trim(),
  };
}

function isMailPrompt(text: string) {
  return /^(send|compose|write)\s+(an?\s+)?mail\b/i.test(text) || /\b(email|mail)\b/i.test(text);
}

function parseMailPrompt(text: string) {
  const match = text.match(/^(?:send|compose|write)\s+(?:an?\s+)?(?:email|mail)(?:\s+to\s+(.+?))?(?:\s+(?:about|regarding|on)\s+(.+))?$/i);
  if (!match) return null;
  return {
    to: match[1]?.trim() || "",
    subject: match[2]?.trim() || "",
  };
}

function parseSchedulePrompt(text: string) {
  const match = text.match(/\b(?:schedule|add event|remind me)\s+(.+?)(?:\s+(?:at|from)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?))?$/i);
  if (!match) return null;
  return {
    title: match[1].trim() || "AURA reminder",
    start: normalizeTime(match[2] || "09:00"),
  };
}

function normalizeTime(raw: string) {
  const clean = raw.trim().toLowerCase();
  const match = clean.match(/^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/);
  if (!match) return "09:00";
  let hour = Number(match[1]);
  const minute = Number(match[2] || "00");
  if (match[3] === "pm" && hour < 12) hour += 12;
  if (match[3] === "am" && hour === 12) hour = 0;
  return `${String(Math.max(0, Math.min(23, hour))).padStart(2, "0")}:${String(Math.max(0, Math.min(59, minute))).padStart(2, "0")}`;
}

function addMinutes(time: string, minutes: number) {
  const [hour, minute] = time.split(":").map(Number);
  const total = Math.max(0, Math.min(23 * 60 + 59, hour * 60 + minute + minutes));
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

function todayKey() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function saveCompanionEvent(title: string, start: string) {
  const key = "aura.schedule.events.v1";
  const fallback: CompanionCalendarEvent[] = [];
  const stored = window.localStorage.getItem(key);
  const current = stored ? JSON.parse(stored) : fallback;
  const events = Array.isArray(current) ? current : fallback;
  const event: CompanionCalendarEvent = {
    id: `companion-event-${Date.now()}`,
    title,
    date: todayKey(),
    start,
    end: addMinutes(start, 30),
    calendar: "Working",
    location: "AURA Companion",
    tone: "blue",
    guests: ["AURA"],
  };
  window.localStorage.setItem(key, JSON.stringify([...events, event]));
  return event;
}

function loadReminderPrefs(): CompanionReminderPrefs {
  if (typeof window === "undefined") {
    return { email: "", phone: "" };
  }
  try {
    const raw = window.localStorage.getItem("aura.companion.reminder-prefs");
    const accountEmail = readAppSettings().accountEmail || "";
    const fallbackEmail = window.localStorage.getItem("aura:reminder-email") || "";
    const fallbackPhone = window.localStorage.getItem("aura:reminder-phone") || "";
    if (!raw) return { email: accountEmail || fallbackEmail, phone: fallbackPhone };
    const parsed = JSON.parse(raw) as Partial<CompanionReminderPrefs>;
    return {
      email: typeof parsed.email === "string" ? parsed.email : (accountEmail || fallbackEmail),
      phone: typeof parsed.phone === "string" ? parsed.phone : fallbackPhone,
    };
  } catch {
    return { email: readAppSettings().accountEmail || window.localStorage.getItem("aura:reminder-email") || "", phone: window.localStorage.getItem("aura:reminder-phone") || "" };
  }
}

function loadReminderItems(): CompanionReminderItem[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const raw = window.localStorage.getItem("aura.companion.reminders");
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((item) => item && typeof item === "object") as CompanionReminderItem[] : [];
  } catch {
    return [];
  }
}

function normalizeAppName(name: string) {
  return name.trim().replace(/\s+/g, " ").replace(/\bapp\b$/i, "").trim();
}

export function AuraCompanionWidget() {
  const isCompanionWindow =
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).get("companion") === "1";
  const [mood, setMood] = useState<Mood>("calm");
  const [prompt, setPrompt] = useState("");
  const [lastReply, setLastReply] = useState(MOOD_COPY.calm);
  const [busy, setBusy] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [model, setModel] = useState(COMPANION_MODELS[0].value);
  const [voiceProfileId, setVoiceProfileId] = useState("piper-en-ljspeech-high");
  const [assistantName, setAssistantName] = useState(() => readAppSettings().assistantName || "AURA");
  const [accountEmail, setAccountEmail] = useState(() => readAppSettings().accountEmail || "");
  const [voiceTone, setVoiceTone] = useState(() => readAppSettings().voiceTone || "Neutral");
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [weatherPanel, setWeatherPanel] = useState<WeatherCurrentResponse["data"] | null>(null);
  const [newsPanel, setNewsPanel] = useState<NewsArticle[]>([]);
  const [musicPlaying, setMusicPlaying] = useState(false);
  const [musicPanel, setMusicPanel] = useState<SpotifyPlayback | null>(null);
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [reminderPrefs, setReminderPrefs] = useState<CompanionReminderPrefs>(() => loadReminderPrefs());
  const [reminders, setReminders] = useState<CompanionReminderItem[]>(() => loadReminderItems());
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [wakeWordEnabled, setWakeWordEnabled] = useState(false);
  const wakeRecognitionRef = useRef<{ start: () => void; stop: () => void; abort?: () => void } | null>(null);

  const todayLabel = useMemo(() => {
    return new Date().toLocaleDateString(undefined, { month: "long", year: "numeric" });
  }, []);

  useEffect(() => {
    auraApi.getVoiceProfiles()
      .then((response) => {
        const projectVoices = (response.profiles || []).filter((profile) => profile.engine === "piper" || profile.engine === "indic_f5" || profile.engine === "indic_parler_tts");
        setVoiceProfiles(projectVoices);
        const firstAvailable = projectVoices.find((profile) => profile.available);
        if (firstAvailable) setVoiceProfileId(firstAvailable.id);
      })
      .catch(() => {
        setVoiceProfiles([]);
      });
  }, []);

  useEffect(() => subscribeToAppSettings(() => {
    const next = readAppSettings();
    setAssistantName(next.assistantName || "AURA");
    setAccountEmail(next.accountEmail || "");
    setVoiceTone(next.voiceTone || "Neutral");
  }), []);

  useEffect(() => {
    void refreshCompanionData();
    const interval = window.setInterval(() => void refreshMusic(false), 3000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    window.localStorage.setItem("aura.companion.reminder-prefs", JSON.stringify(reminderPrefs));
  }, [reminderPrefs]);

  const reminderEmailTarget = reminderPrefs.email.trim() || accountEmail.trim();

  useEffect(() => {
    window.localStorage.setItem("aura.companion.reminders", JSON.stringify(reminders));
  }, [reminders]);

  useEffect(() => {
    if (!wakeWordEnabled) {
      wakeRecognitionRef.current?.stop();
      wakeRecognitionRef.current = null;
      if (mood === "listening") setMood("calm");
      return;
    }
    const speechHost = window as unknown as {
      SpeechRecognition?: new () => any;
      webkitSpeechRecognition?: new () => any;
    };
    const SpeechRecognition = speechHost.SpeechRecognition || speechHost.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setWakeWordEnabled(false);
      setLastReply("Wake word is not available in this browser runtime. Use Mic instead.");
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognition.onresult = (event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => {
      const latest = event.results[event.results.length - 1]?.[0]?.transcript || "";
      const match = latest.match(/hey\s+aura[, ]*(.+)?/i);
      if (!match) return;
      const heardCommand = (match[1] || "").trim();
      setMood("listening");
      if (heardCommand) {
        setPrompt(heardCommand);
        setLastReply(`I heard: ${heardCommand}`);
      } else {
        setLastReply("I am listening.");
      }
    };
    recognition.onend = () => {
      if (wakeWordEnabled) {
        try {
          recognition.start();
        } catch {
          // The browser can reject immediate restarts; the user can toggle again.
        }
      }
    };
    wakeRecognitionRef.current = recognition;
    setMood("listening");
    setLastReply("Wake word is on. Say hey AURA.");
    try {
      recognition.start();
    } catch {
      setWakeWordEnabled(false);
      setLastReply("Microphone permission blocked wake word mode.");
    }
    return () => recognition.stop();
  }, [wakeWordEnabled]);

  async function refreshCompanionData() {
    await Promise.all([refreshMusic(false), refreshMemories()]);
  }

  async function refreshMusic(announce = false) {
    try {
      const current = await spotifyApi.current();
      setMusicPanel(current);
      const isActive = "active" in current ? Boolean(current.active) : false;
      const isPlaying = "isPlaying" in current ? Boolean(current.isPlaying) : false;
      setMusicPlaying(Boolean(isActive && isPlaying));
      if (announce && isActive && current.title) {
        const reply = `${isPlaying ? "Playing" : "Paused"} ${current.title} by ${current.artist || "the current artist"}.`;
        setLastReply(reply);
        void speak(reply);
      }
    } catch {
      setMusicPanel(null);
      setMusicPlaying(false);
    }
  }

  async function refreshMemories() {
    try {
      setMemories((await auraApi.listMemories()).slice(0, 3));
    } catch {
      setMemories([]);
    }
  }

  async function speak(text: string) {
    if (!voiceEnabled) return;
    const selectedProfile = voiceProfiles.find((profile) => profile.id === voiceProfileId);
    if (!selectedProfile) {
      setLastReply("No local open-source voice profile is loaded yet.");
      return;
    }
    setMood("speaking");
    void playExpressionFx("speaking");
    try {
      const language = selectedProfile.languages?.[0] || "en";
      await auraApi.speakText(text, language, voiceProfileId);
      setMood("calm");
    } catch {
      setMood("calm");
      setLastReply(`Voice is not ready: ${selectedProfile.reason || "install the Piper voice assets first."}`);
    }
  }

  async function askCompanion(event: FormEvent) {
    event.preventDefault();
    const clean = prompt.trim();
    if (!clean || busy) return;
    setPrompt("");
    setBusy(true);
    setMood("thinking");
    setWeatherPanel(null);
    setNewsPanel([]);
    try {
      const requestedMediaAction = mediaAction(clean);
      if (requestedMediaAction) {
        setMood("music");
        void playExpressionFx("music");
        if (requestedMediaAction === "next") await spotifyApi.next();
        if (requestedMediaAction === "previous") await spotifyApi.previous();
        if (requestedMediaAction === "playpause") await spotifyApi.playpause();
        const current = await spotifyApi.current();
        const isCurrentPlaying = "isPlaying" in current ? Boolean(current.isPlaying) : false;
        const isCurrentActive = "active" in current ? Boolean(current.active) : false;
        setMusicPanel(current);
        setMusicPlaying(isCurrentPlaying);
        const reply = isCurrentActive && current.title
          ? `${isCurrentPlaying ? "Playing" : "Paused"} ${current.title} by ${current.artist || "the current artist"}.`
          : "I sent the media key. Start music in your player if nothing is active.";
        setLastReply(reply);
        void speak(reply);
        return;
      }

      const openAndSearch = parseOpenAndSearch(clean);
      if (openAndSearch) {
        const appName = normalizeAppName(openAndSearch.app);
        const openResult = await auraApi.sendMessage(`open ${appName}`);
        const appReply = openResult.text || `Opened ${appName}.`;
        if (openAndSearch.action === "search" || openAndSearch.action === "google") {
          const query = openAndSearch.query;
          void window.aura?.media.openExternal(`https://www.google.com/search?q=${encodeURIComponent(query)}`);
          setLastReply(`${appReply} Searching Google for ${query}.`);
          void speak(`${appReply} Searching Google for ${query}.`);
          return;
        }
        if (openAndSearch.action === "play") {
          const query = openAndSearch.query;
          if (/youtube/i.test(appName)) {
            const yt = await youtubeApi.search(query);
            if (yt.ok && yt.results[0]) {
              await youtubeApi.openMini(yt.results[0].id);
              setLastReply(`Playing ${yt.results[0].title} on YouTube.`);
              void playExpressionFx("music");
              void speak(`Playing ${yt.results[0].title} on YouTube.`);
              return;
            }
            await window.aura?.media.openExternal(`https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`);
            setLastReply(`I opened YouTube search for ${query}.`);
            void speak(`I opened YouTube search for ${query}.`);
            return;
          }
          if (/spotify/i.test(appName)) {
            const search = await spotifyApi.search(query);
            const topTrack = search.results?.[0];
            if (topTrack?.uri) {
              await spotifyApi.play(topTrack.uri);
              setMusicPanel({ ...topTrack, ok: true, active: true, isPlaying: true });
              setMusicPlaying(true);
              setLastReply(`Playing ${topTrack.title} by ${topTrack.artist}.`);
              void playExpressionFx("music");
              void speak(`Playing ${topTrack.title} by ${topTrack.artist}.`);
              return;
            }
            setLastReply(`I opened Spotify search for ${query}.`);
            void speak(`I opened Spotify search for ${query}.`);
            return;
          }
          setLastReply(`${appReply} I could not match a media player for ${query}.`);
          void speak(`${appReply} I could not match a media player for ${query}.`);
          return;
        }
      }

      if (/^(remember|save memory)\b/i.test(clean)) {
        const response = await auraApi.sendMessage(clean);
        const reply = response.text || "I saved that to memory.";
        setLastReply(reply);
        void playExpressionFx("happy");
        await refreshMemories();
        void speak(reply);
        return;
      }

      const scheduleDraft = parseSchedulePrompt(clean);
      if (scheduleDraft) {
        const event = saveCompanionEvent(scheduleDraft.title, scheduleDraft.start);
        const reply = `Scheduled ${event.title} today at ${event.start}.`;
        setLastReply(reply);
        void playExpressionFx("happy");
        void auraApi.sendMessage(`remember schedule: ${event.title} on ${event.date} at ${event.start}`);
        setReminders((current) => [
          {
            id: `reminder-${event.id}`,
            title: event.title,
            time: event.start,
            note: "Calendar reminder",
            date: event.date,
          },
          ...current,
        ].slice(0, 10));
        if (reminderEmailTarget) {
          const subject = encodeURIComponent(`AURA reminder: ${event.title}`);
          const body = encodeURIComponent(`Reminder set for ${event.title} on ${event.date} at ${event.start}.`);
          void window.aura?.media.openExternal(`mailto:${encodeURIComponent(reminderEmailTarget)}?subject=${subject}&body=${body}`);
        }
        void speak(reply);
        return;
      }

      if (/^open\s+(file|document|folder)\b/i.test(clean)) {
        await openSelectedFile();
        return;
      }

      if (isOpenAppPrompt(clean)) {
        const response = await auraApi.sendMessage(clean);
        const reply = response.text || "I sent the local app open command.";
        setLastReply(reply);
        void speak(reply);
        return;
      }

      if (isMailPrompt(clean)) {
        const mail = parseMailPrompt(clean);
        const to = mail?.to ? mail.to.replace(/^\s+|\s+$/g, "") : "";
        const subject = mail?.subject ? `?subject=${encodeURIComponent(mail.subject)}` : "";
        const mailto = to ? `mailto:${encodeURIComponent(to)}${subject}` : "mailto:";
        await window.aura?.media.openExternal(mailto);
        const reply = to ? `I opened a mail draft for ${to}.` : "I opened a new mail draft.";
        setLastReply(reply);
        void playExpressionFx("thinking");
        void speak(reply);
        return;
      }

      if (isSearchPrompt(clean)) {
        const query = cleanSearchQuery(clean) || clean;
        const response = await auraApi.webSearch(query, 4);
        const reply = response.results?.length
          ? `I found ${response.results.length} web results for ${query}.`
          : `I opened Google search for ${query}.`;
        setLastReply(reply);
        if (response.results?.length) {
          setNewsPanel(response.results.map((result, index) => ({
            id: `web-${index}-${result.url}`,
            title: result.title,
            excerpt: result.snippet || result.domain,
            url: result.url,
            source: result.domain,
            category: "Web",
            published_at: "",
          })));
        }
        void window.aura?.media.openExternal(`https://www.google.com/search?q=${encodeURIComponent(query)}`);
        void playExpressionFx("thinking");
        void speak(reply);
        return;
      }

      if (isWeatherPrompt(clean)) {
        setMood("weather");
        const response = await auraApi.getWeather(locationFromPrompt(clean) || undefined);
        if (!response.ok) throw new Error(response.error?.message || "Weather is unavailable.");
        setWeatherPanel(response.data);
        const weather = response.data.formatted_weather;
        const place = response.data.location?.name || "your location";
        const reply = weather?.message || `Weather in ${place}: ${weather?.temperature ?? "--"} degrees, ${weather?.condition || "current conditions"}.`;
        setLastReply(reply);
        void playExpressionFx("weather");
        void playCompanionTone(weather?.condition || "");
        void speak(reply);
        return;
      }

      if (isNewsPrompt(clean)) {
        setMood("news");
        const response = await auraApi.getNews("All", "", 4);
        if (!response.ok) throw new Error(response.error?.message || "News is unavailable.");
        const headlines = response.data.articles || [];
        setNewsPanel(headlines);
        const reply = headlines.length
          ? `Here are today's top headlines. ${headlines.slice(0, 3).map((article, index) => `${index + 1}. ${article.title}`).join(". ")}.`
          : "I could not find fresh headlines right now.";
        setLastReply(reply);
        void playExpressionFx("news");
        void playCompanionTone("news");
        if (headlines[0]?.image_url) {
          setNewsPanel(headlines);
        }
        void speak(reply);
        return;
      }

      const companionPrompt = [
        `/ollama ${model}`,
        "You are AURA's small companion widget. Reply warmly, briefly, and naturally.",
        "Keep the answer good for text-to-speech. No markdown unless the user asks.",
        clean,
      ].join(" ");
      const response = await auraApi.sendMessage(companionPrompt);
      const reply = response.spoken_text || response.text || "Done.";
      setLastReply(reply);
      void speak(reply);
    } catch {
      const reply = "I could not reach the local AURA runtime, but I am still here.";
      setLastReply(reply);
      void speak(reply);
    } finally {
      setBusy(false);
      if (!voiceEnabled) setMood("calm");
    }
  }

  function chooseMood(next: Mood) {
    setMood(next);
    setLastReply(MOOD_COPY[next]);
    void playExpressionFx(next);
    void speak(MOOD_COPY[next]);
  }

  async function openSelectedFile() {
    setBusy(true);
    setMood("thinking");
    try {
      const selectedPath = await window.aura?.media.selectFile();
      if (!selectedPath) {
        setLastReply("No file selected.");
        return;
      }
      const result = await window.aura?.media.openPath(selectedPath);
      const reply = result?.ok ? "Opened the selected file." : result?.message || "I could not open that file.";
      setLastReply(reply);
      void speak(reply);
    } finally {
      setBusy(false);
      setMood("calm");
    }
  }

  async function toggleVoiceInput() {
    if (voiceBusy) return;
    setVoiceBusy(true);
    try {
      const voiceState = await auraApi.getVoiceState();
      if (voiceState.state === "RECORDING") {
        const result = await auraApi.stopVoice();
        if (result?.text) {
          setPrompt(result.text);
          setLastReply(result.text);
        }
      } else {
        await auraApi.startVoice();
        setMood("listening");
        void playExpressionFx("listening");
        setLastReply("Listening for you.");
      }
    } finally {
      setVoiceBusy(false);
    }
  }

  async function runQuickAction(action: "file" | "calculator" | "weather" | "news" | "search" | "remember" | "schedule") {
    if (action === "file") {
      await openSelectedFile();
      return;
    }
    if (action === "calculator") {
      setPrompt("open calculator");
      return;
    }
    if (action === "weather") {
      setPrompt("weather today");
      return;
    }
    if (action === "news") {
      setPrompt("news today");
      return;
    }
    if (action === "search") {
      setPrompt("google ");
      return;
    }
    if (action === "remember") {
      setPrompt("remember ");
      return;
    }
    setPrompt("schedule ");
  }

  function setReminderContact(field: keyof CompanionReminderPrefs, value: string) {
    setReminderPrefs((current) => ({ ...current, [field]: value }));
  }

  async function playCompanionTone(kind: string) {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass || !voiceEnabled) return;
    const ctx = new AudioContextClass();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const condition = kind.toLowerCase();
    osc.type = condition.includes("rain") ? "triangle" : condition.includes("news") ? "square" : "sine";
    osc.frequency.value = condition.includes("rain") ? 164 : condition.includes("cloud") ? 220 : condition.includes("news") ? 330 : 440;
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.025, ctx.currentTime + 0.04);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.42);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.45);
  }

  async function playExpressionFx(kind: Mood | "news" | "music" | "speaking" | "listening") {
    if (!voiceEnabled) return;
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass) return;
    const ctx = new AudioContextClass();
    const gain = ctx.createGain();
    gain.gain.value = 0.0001;
    gain.connect(ctx.destination);

    const playTone = (frequency: number, type: OscillatorType, start: number, duration: number, volume = 0.02) => {
      const osc = ctx.createOscillator();
      const env = ctx.createGain();
      osc.type = type;
      osc.frequency.value = frequency;
      osc.connect(env);
      env.connect(gain);
      env.gain.setValueAtTime(0.0001, start);
      env.gain.exponentialRampToValueAtTime(volume, start + 0.03);
      env.gain.exponentialRampToValueAtTime(0.0001, start + duration);
      osc.start(start);
      osc.stop(start + duration + 0.02);
    };

    const now = ctx.currentTime;
    switch (kind) {
      case "happy":
        playTone(660, "sine", now, 0.12, 0.018);
        playTone(880, "triangle", now + 0.08, 0.12, 0.016);
        break;
      case "sleepy":
        playTone(220, "sine", now, 0.2, 0.012);
        playTone(165, "sine", now + 0.18, 0.26, 0.01);
        break;
      case "weather":
        playTone(392, "triangle", now, 0.18, 0.016);
        playTone(523, "triangle", now + 0.12, 0.18, 0.014);
        break;
      case "news":
        playTone(260, "square", now, 0.08, 0.01);
        playTone(330, "square", now + 0.08, 0.08, 0.01);
        break;
      case "music":
        playTone(196, "sine", now, 0.12, 0.014);
        playTone(247, "sine", now + 0.1, 0.12, 0.014);
        playTone(294, "triangle", now + 0.2, 0.12, 0.014);
        break;
      case "surprised":
        playTone(784, "triangle", now, 0.08, 0.014);
        playTone(988, "triangle", now + 0.08, 0.08, 0.012);
        break;
      case "laugh":
        playTone(523, "sine", now, 0.06, 0.01);
        playTone(659, "sine", now + 0.08, 0.06, 0.01);
        playTone(784, "sine", now + 0.16, 0.06, 0.01);
        break;
      case "listening":
        playTone(440, "sine", now, 0.08, 0.012);
        playTone(554, "sine", now + 0.09, 0.08, 0.01);
        break;
      case "speaking":
        playTone(330, "triangle", now, 0.1, 0.014);
        break;
      default:
        playTone(440, "sine", now, 0.08, 0.01);
        break;
    }
  }

  return (
    <section className={`aura-companion-card mood-${mood} ${musicPlaying ? "is-music-playing" : ""}`} aria-label="AI Assistant companion">
      <header className="aura-companion-head">
        <div>
          <h3>{assistantName}</h3>
          <span>{todayLabel}</span>
        </div>
        <div className="aura-companion-window-dots" aria-hidden="true">
          <i />
          <i />
        </div>
        {isCompanionWindow && (
          <button
            type="button"
            className="aura-companion-close-btn"
            onClick={() => void window.aura?.window.close()}
            title="Exit AURA"
            aria-label="Exit AURA"
          >
            x
          </button>
        )}
      </header>

      <div className="aura-companion-stage" onClick={() => chooseMood(mood === "happy" ? "calm" : "happy")}>
        <div className="aura-dot-grid" aria-hidden="true" />
        {mood === "news" && <div className="aura-news-prop" aria-hidden="true" />}
        <div className="aura-expression">
          <span className="aura-expression-eye" />
          <span className="aura-expression-body" />
        </div>
        <div className="aura-speech-bubble">
          <p>{busy ? "Thinking..." : lastReply}</p>
        </div>
      </div>

      {(weatherPanel || newsPanel.length > 0 || musicPlaying) && (
        <div className="aura-companion-live-panel">
          {weatherPanel?.formatted_weather && (
            <>
              <strong>{weatherPanel.location?.name || "Weather"}</strong>
              <span>{weatherPanel.formatted_weather.condition}</span>
              <span>{weatherPanel.formatted_weather.temperature} deg, feels {weatherPanel.formatted_weather.feels_like ?? "--"} deg</span>
            </>
          )}
          {newsPanel.slice(0, 3).map((article) => (
            <button key={article.id} type="button" onClick={() => window.aura?.media.openExternal(article.url)} title={article.source} className={article.image_url ? "aura-news-card-link has-image" : "aura-news-card-link"}>
              {article.image_url && <img src={article.image_url} alt="" aria-hidden="true" />}
              <span>
                <strong>{article.title}</strong>
                <small>{article.source}</small>
              </span>
            </button>
          ))}
          {musicPlaying && musicPanel?.title && (
            <div className="aura-companion-track-banner">
              {musicPanel.imageUrl && <img src={musicPanel.imageUrl} alt="" aria-hidden="true" />}
              <span><strong>{musicPanel.title}</strong><small>{musicPanel.artist || musicPanel.device || "Windows media"}</small></span>
            </div>
          )}
        </div>
      )}

      <div className="aura-companion-actions" aria-label="Quick companion actions">
        <button type="button" onClick={() => void runQuickAction("file")}>Open file</button>
        <button type="button" onClick={() => void runQuickAction("calculator")}>Open app</button>
        <button type="button" onClick={() => void runQuickAction("search")}>Google</button>
        <button type="button" onClick={() => void runQuickAction("schedule")}>Schedule</button>
        <button type="button" onClick={() => void runQuickAction("remember")}>Memory</button>
        <button type="button" onClick={() => void runQuickAction("news")}>News</button>
        <button type="button" onClick={() => void runQuickAction("weather")}>Weather</button>
      </div>

      <form className="aura-companion-composer" onSubmit={askCompanion}>
        <input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Talk to AURA..." />
        <button type="submit" disabled={!prompt.trim() || busy} title="Ask and speak">Ask</button>
      </form>

      <section className="aura-companion-music-card" aria-label="Companion music controls">
        <div>
          <strong>{musicPanel?.active ? musicPanel.title : "Music"}</strong>
          <span>{musicPanel?.active ? musicPanel.artist || musicPanel.device || "Windows media session" : "No media playing"}</span>
        </div>
        <div className="aura-companion-music-controls">
          <button type="button" onClick={() => void spotifyApi.previous().then(() => refreshMusic(true))} title="Previous">‹</button>
          <button type="button" onClick={() => void spotifyApi.playpause().then(() => refreshMusic(true))} title="Play or pause">
            {musicPlaying ? "Pause" : "Play"}
          </button>
          <button type="button" onClick={() => void spotifyApi.next().then(() => refreshMusic(true))} title="Next">›</button>
        </div>
      </section>

      <div className="aura-companion-controls">
        <label>
          <span>Model</span>
          <select value={model} onChange={(event) => setModel(event.target.value)} title="Companion Ollama model">
            {COMPANION_MODELS.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Voice</span>
          <select value={voiceProfileId} onChange={(event) => setVoiceProfileId(event.target.value)} title="Project voice model">
            {voiceProfiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.display_name}{profile.available ? "" : " (setup needed)"}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Tone</span>
          <select value={voiceTone} onChange={(event) => setVoiceTone(event.target.value)} title="Companion voice tone">
            {["Neutral", "Male", "Female", "Boyfriend", "Girlfriend", "Soft male", "Soft female"].map((tone) => (
              <option key={tone} value={tone}>{tone}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="aura-mood-row" aria-label="Expression controls">
        {(["calm", "happy", "thinking", "sleepy", "music"] as Mood[]).map((item) => (
          <button key={item} type="button" className={mood === item ? "active" : ""} onClick={() => chooseMood(item)}>
            {item}
          </button>
        ))}
      </div>

      <div className="aura-companion-bottom">
        <div className="aura-mini-card aura-task-card">
          <div><strong>Memory</strong><button type="button" onClick={() => void refreshMemories()}>+</button></div>
          {memories.length === 0 && <span>No memories yet</span>}
          {memories.map((memory) => <span key={memory.id || memory.content}>{memory.content}</span>)}
        </div>
        <div className="aura-mini-card aura-doc-card">
          <strong>Docs</strong>
          <div className="aura-doc-thumb" />
          <span>Learn Design</span>
        </div>
      </div>

      <div className="aura-companion-reminders">
        <div className="aura-mini-card">
          <strong>Reminders</strong>
          {reminders.length === 0 && <span>No reminders yet</span>}
          {reminders.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                if (!reminderEmailTarget) return;
                void window.aura?.media.openExternal(`mailto:${encodeURIComponent(reminderEmailTarget)}?subject=${encodeURIComponent(item.title)}&body=${encodeURIComponent(item.note || item.time)}`);
              }}
            >
              {item.title} <small>{item.time}</small>
            </button>
          ))}
        </div>
        <div className="aura-mini-card">
          <strong>Reminder contact</strong>
          <input
            value={reminderPrefs.email}
            onChange={(event) => setReminderContact("email", event.target.value)}
            placeholder="Email for reminder drafts"
          />
          <input
            value={reminderPrefs.phone}
            onChange={(event) => setReminderContact("phone", event.target.value)}
            placeholder="Phone or SMS gateway"
          />
        </div>
      </div>

      <footer className="aura-companion-foot">
        <button type="button" className={voiceEnabled ? "active" : ""} title="Toggle voice" onClick={() => setVoiceEnabled((prev) => !prev)}>Voice</button>
        <button type="button" title="Voice input" onClick={() => void toggleVoiceInput()}>Mic</button>
        <button type="button" className={wakeWordEnabled ? "active" : ""} title="Wake word" onClick={() => setWakeWordEnabled((enabled) => !enabled)}>Hey</button>
        <button type="button" className="aura-core-toggle" title="Speak last reply" onClick={() => void speak(lastReply)}>*</button>
        <button type="button" title="Reset mood" onClick={() => chooseMood("calm")}>Reset</button>
      </footer>
    </section>
  );
}
