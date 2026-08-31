import { app, BrowserWindow, dialog, globalShortcut, ipcMain, nativeTheme, shell, Tray, Menu, session } from "electron";
import { execFile } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import os from "node:os";
import { promisify } from "node:util";
import { IPC_CHANNELS } from "./ipcChannels.js";
import { validateAuraRequest } from "./ipcSchema.js";
import { PythonBridge } from "./pythonBridge.js";

const execFileAsync = promisify(execFile);

const isPackagedAsar = __dirname.includes("app.asar");
const projectRoot = isPackagedAsar ? path.join(process.resourcesPath, "app.asar") : path.resolve(__dirname, "..");
const pythonRoot = isPackagedAsar ? path.join(process.resourcesPath, "app.asar.unpacked") : projectRoot;
const startupLog = path.join(pythonRoot, "aura-electron-startup.log");
const bridge = new PythonBridge(projectRoot, pythonRoot);
let mainWindow: InstanceType<typeof BrowserWindow> | null = null;
let companionWindow: InstanceType<typeof BrowserWindow> | null = null;
let tray: InstanceType<typeof Tray> | null = null;
let isQuitting = false;

function companionBoundsPath(): string {
  return path.join(app.getPath("userData"), "aura-companion-window.json");
}

function providerKeysPath(): string {
  return path.join(app.getPath("userData"), "aura-provider-keys.json");
}
const spotifyScopes = [
  "user-read-playback-state",
  "user-modify-playback-state",
  "user-read-currently-playing",
  "user-read-private",
].join(" ");
const spotifyRedirectPort = 43879;
const spotifyRedirectUri = `http://127.0.0.1:${spotifyRedirectPort}/callback`;

function logStartup(message: string): void {
  try {
    fs.appendFileSync(startupLog, `${new Date().toISOString()} ${message}\n`, "utf8");
  } catch {
    // Logging must never prevent startup.
  }
}

function readEnvValue(name: string): string | undefined {
  if (process.env[name]) {
    return process.env[name];
  }
  const envPath = path.join(pythonRoot, ".env");
  try {
    const lines = fs.readFileSync(envPath, "utf8").split(/\r?\n/);
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) {
        continue;
      }
      const [key, ...rest] = trimmed.split("=");
      if (key.trim() === name) {
        return rest.join("=").trim().replace(/^["']|["']$/g, "");
      }
    }
  } catch {
    return undefined;
  }
  return undefined;
}

async function spotifyFetch(pathname: string, options: RequestInit = {}): Promise<unknown> {
  const accessToken = await getSpotifyAccessToken();
  if (!accessToken) {
    return {
      ok: false,
      needsAuth: true,
      message: "Connect Spotify to show playback and controls.",
    };
  }

  let response: Response;
  try {
    response = await fetch(`https://api.spotify.com/v1${pathname}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
  } catch (error) {
    logStartup(`spotifyFetchNetworkError:${error instanceof Error ? error.message : String(error)}`);
    return {
      ok: false,
      active: false,
      networkUnavailable: true,
      message: "Spotify network is unavailable. Windows media controls may still work if a local media session is active.",
    };
  }

  if (response.status === 204) {
    return { ok: true };
  }

  const text = await response.text();
  let body: any = {};
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = { error: { message: text } };
    }
  }
  if (!response.ok) {
    return {
      ok: false,
      status: response.status,
      message: body?.error?.message || response.statusText,
    };
  }
  return { ok: true, data: body };
}

type SpotifyTokenStore = {
  accessToken: string;
  refreshToken?: string;
  expiresAt: number;
};

function spotifyAuthPath(): string {
  return path.join(app.getPath("userData"), "spotify-auth.json");
}

function readSpotifyAuth(): SpotifyTokenStore | null {
  const envToken = readEnvValue("SPOTIFY_ACCESS_TOKEN");
  if (envToken) {
    return { accessToken: envToken, expiresAt: Date.now() + 3_600_000 };
  }
  try {
    return JSON.parse(fs.readFileSync(spotifyAuthPath(), "utf8")) as SpotifyTokenStore;
  } catch {
    return null;
  }
}

function writeSpotifyAuth(tokens: SpotifyTokenStore): void {
  fs.mkdirSync(path.dirname(spotifyAuthPath()), { recursive: true });
  fs.writeFileSync(spotifyAuthPath(), JSON.stringify(tokens, null, 2), "utf8");
}

async function getSpotifyAccessToken(): Promise<string | null> {
  const auth = readSpotifyAuth();
  if (!auth) {
    return null;
  }
  if (auth.expiresAt > Date.now() + 60_000) {
    return auth.accessToken;
  }
  if (!auth.refreshToken) {
    return auth.accessToken;
  }
  const clientId = readEnvValue("SPOTIFY_CLIENT_ID");
  if (!clientId) {
    return null;
  }
  const response = await fetch("https://accounts.spotify.com/api/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: clientId,
      grant_type: "refresh_token",
      refresh_token: auth.refreshToken,
    }),
  });
  const body = await response.json() as { access_token?: string; refresh_token?: string; expires_in?: number };
  if (!response.ok || !body.access_token) {
    return null;
  }
  const next = {
    accessToken: body.access_token,
    refreshToken: body.refresh_token || auth.refreshToken,
    expiresAt: Date.now() + (body.expires_in || 3600) * 1000,
  };
  writeSpotifyAuth(next);
  return next.accessToken;
}

async function connectSpotify(): Promise<unknown> {
  const clientId = readEnvValue("SPOTIFY_CLIENT_ID");
  if (!clientId) {
    return { ok: false, needsClientId: true, message: "SPOTIFY_CLIENT_ID is missing in .env." };
  }

  const verifier = crypto.randomBytes(64).toString("base64url");
  const challenge = crypto.createHash("sha256").update(verifier).digest("base64url");
  const state = crypto.randomBytes(16).toString("hex");

  return new Promise((resolve) => {
    const server = http.createServer(async (request, response) => {
      try {
        const requestUrl = new URL(request.url || "/", "http://127.0.0.1");
        const code = requestUrl.searchParams.get("code");
        const returnedState = requestUrl.searchParams.get("state");
        if (!code || returnedState !== state) {
          throw new Error("Spotify authorization was cancelled.");
        }
        const tokenResponse = await fetch("https://accounts.spotify.com/api/token", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({
            client_id: clientId,
            grant_type: "authorization_code",
            code,
            redirect_uri: spotifyRedirectUri,
            code_verifier: verifier,
          }),
        });
        const tokenBody = await tokenResponse.json() as { access_token?: string; refresh_token?: string; expires_in?: number; error_description?: string };
        if (!tokenResponse.ok || !tokenBody.access_token) {
          throw new Error(tokenBody.error_description || "Spotify token exchange failed.");
        }
        writeSpotifyAuth({
          accessToken: tokenBody.access_token,
          refreshToken: tokenBody.refresh_token,
          expiresAt: Date.now() + (tokenBody.expires_in || 3600) * 1000,
        });
        response.writeHead(200, { "Content-Type": "text/html" });
        response.end("<h2>Spotify connected. You can return to AURA.</h2>");
        server.close();
        resolve({ ok: true });
      } catch (error) {
        response.writeHead(400, { "Content-Type": "text/html" });
        response.end("<h2>Spotify connection failed.</h2>");
        server.close();
        resolve({ ok: false, message: error instanceof Error ? error.message : "Spotify connection failed." });
      }
    });

    server.listen(spotifyRedirectPort, "127.0.0.1", () => {
      const authUrl = new URL("https://accounts.spotify.com/authorize");
      authUrl.searchParams.set("client_id", clientId);
      authUrl.searchParams.set("response_type", "code");
      authUrl.searchParams.set("redirect_uri", spotifyRedirectUri);
      authUrl.searchParams.set("scope", spotifyScopes);
      authUrl.searchParams.set("state", state);
      authUrl.searchParams.set("code_challenge_method", "S256");
      authUrl.searchParams.set("code_challenge", challenge);
      void shell.openExternal(authUrl.toString());
    });
  });
}

function mapSpotifyPlayback(raw: any): unknown {
  if (!raw?.ok) {
    return raw;
  }
  const data = raw.data;
  const item = data?.item;
  if (!item) {
    return { ok: true, active: false };
  }
  return {
    ok: true,
    active: true,
    isPlaying: Boolean(data.is_playing),
    progressMs: data.progress_ms || 0,
    durationMs: item.duration_ms || 0,
    title: item.name || "Spotify",
    artist: Array.isArray(item.artists) ? item.artists.map((artist: { name?: string }) => artist.name).filter(Boolean).join(", ") : item.show?.name || "",
    album: item.album?.name || item.type || "",
    imageUrl: item.album?.images?.[0]?.url || item.images?.[0]?.url || "",
    uri: item.uri,
    externalUrl: item.external_urls?.spotify,
    device: data.device?.name || "",
  };
}

const artworkCache = new Map<string, string>();

async function fetchPublicArtwork(title: string, artist: string): Promise<string> {
  const key = `${title.toLowerCase().trim()} - ${artist.toLowerCase().trim()}`;
  if (artworkCache.has(key)) {
    return artworkCache.get(key) || "";
  }
  const cleanTitle = title.replace(/\s*-\s*(Extended|From|Original|Remix|Remastered).*$/i, "").trim();
  const query = `${cleanTitle} ${artist}`.trim();
  if (!query) return "";

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2500);
    const res = await fetch(`https://itunes.apple.com/search?term=${encodeURIComponent(query)}&media=music&limit=1`, {
      headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" },
      signal: controller.signal,
    });
    clearTimeout(timeout);
    const data = await res.json() as { results?: Array<{ artworkUrl100?: string }> };
    if (data?.results?.[0]?.artworkUrl100) {
      const highRes = data.results[0].artworkUrl100.replace("100x100bb", "600x600bb");
      artworkCache.set(key, highRes);
      return highRes;
    }
  } catch {
    // Network or timeout fallback
  }
  artworkCache.set(key, "");
  return "";
}

async function getWindowsMediaSession(action: string = "current"): Promise<any> {
  const scriptPath = path.join(pythonRoot, "scripts", "windows_media.ps1");
  try {
    const { stdout } = await execFileAsync(
      "powershell",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", scriptPath, "-Action", action],
      { timeout: 4000 }
    );
    const trimmed = stdout.trim();
    if (trimmed) {
      const data = JSON.parse(trimmed);
      if (data && data.ok && data.active && data.title && !data.imageUrl) {
        data.imageUrl = await fetchPublicArtwork(data.title, data.artist || "");
      }
      return data;
    }
  } catch (error) {
    logStartup(`windowsMediaSessionError: ${error instanceof Error ? error.message : String(error)}`);
  }
  return { ok: false, active: false };
}

async function handleSpotifyRequest(raw: unknown): Promise<unknown> {
  const request = raw as { action?: string; payload?: Record<string, unknown> };
  const action = request?.action;
  const payload = request?.payload || {};

  if (action === "current") {
    const winMedia = await getWindowsMediaSession("current");
    if (winMedia && winMedia.ok && winMedia.active && winMedia.title) {
      return winMedia;
    }
    return mapSpotifyPlayback(await spotifyFetch("/me/player"));
  }
  if (action === "connect") {
    return connectSpotify();
  }
  if (action === "disconnect") {
    try {
      fs.rmSync(spotifyAuthPath(), { force: true });
    } catch {
      // Already disconnected.
    }
    return { ok: true };
  }
  if (action === "pause" || action === "play" || action === "playpause" || action === "next" || action === "previous") {
    const winRes = await getWindowsMediaSession(action);
    if (winRes && winRes.ok) {
      return winRes;
    }
  }
  if (action === "pause") {
    return spotifyFetch("/me/player/pause", { method: "PUT" });
  }
  if (action === "play") {
    const uri = typeof payload.uri === "string" ? payload.uri : undefined;
    return spotifyFetch("/me/player/play", { method: "PUT", body: uri ? JSON.stringify({ uris: [uri] }) : undefined });
  }
  if (action === "next") {
    return spotifyFetch("/me/player/next", { method: "POST" });
  }
  if (action === "previous") {
    return spotifyFetch("/me/player/previous", { method: "POST" });
  }
  if (action === "volume") {
    const volume = Math.max(0, Math.min(100, Number(payload.volume || 0)));
    return spotifyFetch(`/me/player/volume?volume_percent=${volume}`, { method: "PUT" });
  }
  if (action === "seek") {
    const positionMs = Math.max(0, Number(payload.positionMs || 0));
    return spotifyFetch(`/me/player/seek?position_ms=${Math.round(positionMs)}`, { method: "PUT" });
  }
  if (action === "search") {
    const query = String(payload.query || "").trim();
    if (!query) {
      throw new Error("Spotify search requires a query.");
    }
    const rawResult = await spotifyFetch(`/search?type=track&limit=5&q=${encodeURIComponent(query)}`);
    if (!(rawResult as { ok?: boolean }).ok) {
      return rawResult;
    }
    const items = ((rawResult as any).data?.tracks?.items || []).map((track: any) => ({
      id: track.id,
      title: track.name,
      artist: Array.isArray(track.artists) ? track.artists.map((artist: { name?: string }) => artist.name).filter(Boolean).join(", ") : "",
      album: track.album?.name || "",
      imageUrl: track.album?.images?.[0]?.url || "",
      uri: track.uri,
      externalUrl: track.external_urls?.spotify,
      durationMs: track.duration_ms || 0,
    }));
    return { ok: true, results: items };
  }

  throw new Error("Unsupported Spotify action.");
}

process.on("uncaughtException", (error) => logStartup(`uncaughtException ${error.stack || error.message}`));
process.on("unhandledRejection", (reason) => logStartup(`unhandledRejection ${String(reason)}`));

function createWindow(): void {
  logStartup("createWindow:start");
  mainWindow = new BrowserWindow({
    width: 1240,
    height: 820,
    minWidth: 960,
    minHeight: 680,
    title: "AURA ASUS",
    titleBarStyle: "hidden",
    trafficLightPosition: { x: 16, y: 16 },
    backgroundColor: nativeTheme.shouldUseDarkColors ? "#111315" : "#f4f2ef",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      devTools: true,
    },
  });

  const rendererUrl = process.env.AURA_RENDERER_URL;
  if (rendererUrl) {
    logStartup(`loadURL:${rendererUrl}`);
    mainWindow.loadURL(rendererUrl);
  } else {
    logStartup("loadFile:dist/index.html");
    mainWindow.loadFile(path.join(projectRoot, "dist", "index.html"));
  }

  mainWindow.webContents.on("did-fail-load", (_event, errorCode, errorDescription, validatedURL) => {
    logStartup(`did-fail-load:${errorCode}:${errorDescription}:${validatedURL}`);
  });
  mainWindow.webContents.on("render-process-gone", (_event, details) => {
    logStartup(`render-process-gone:${JSON.stringify(details)}`);
  });
  mainWindow.webContents.on("did-finish-load", () => {
    logStartup("did-finish-load");
  });
  mainWindow.webContents.on("console-message", (_event, level, message, line, sourceId) => {
    logStartup(`console:${level}:${sourceId}:${line}:${message}`);
  });

  mainWindow.on("minimize", () => {
    createCompanionWindow();
  });

  mainWindow.on("close", (event) => {
    if (isQuitting) {
      return;
    }
    event.preventDefault();
    mainWindow?.hide();
    createCompanionWindow();
  });

  bridge.on("event", (event) => {
    logStartup(`backendEvent:${JSON.stringify(event)}`);
    if (mainWindow && !mainWindow.isDestroyed() && !mainWindow.webContents.isDestroyed()) {
      mainWindow.webContents.send(IPC_CHANNELS.backendEvent, event);
    }
  });
  bridge.start();
  logStartup("createWindow:done");
}

function createCompanionWindow(): void {
  if (companionWindow && !companionWindow.isDestroyed()) {
    companionWindow.show();
    return;
  }

  let savedBounds: { width?: number; height?: number; x?: number; y?: number } | null = null;
  try {
    savedBounds = JSON.parse(fs.readFileSync(companionBoundsPath(), "utf8")) as { width?: number; height?: number; x?: number; y?: number };
  } catch {
    savedBounds = null;
  }

  companionWindow = new BrowserWindow({
    width: savedBounds?.width || 330,
    height: savedBounds?.height || 520,
    x: savedBounds?.x,
    y: savedBounds?.y,
    minWidth: 260,
    minHeight: 360,
    title: "AURA Companion",
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    movable: true,
    show: false,
    backgroundColor: "#00000000",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      devTools: true,
    },
  });

  const rendererUrl = process.env.AURA_RENDERER_URL;
  if (rendererUrl) {
    const companionUrl = new URL(rendererUrl);
    companionUrl.searchParams.set("companion", "1");
    companionWindow.loadURL(companionUrl.toString());
  } else {
    companionWindow.loadFile(path.join(projectRoot, "dist", "index.html"), { search: "companion=1" });
  }

  companionWindow.once("ready-to-show", () => companionWindow?.show());
  companionWindow.on("move", () => {
    if (!companionWindow || companionWindow.isDestroyed()) return;
    try {
      fs.writeFileSync(companionBoundsPath(), JSON.stringify(companionWindow.getBounds(), null, 2), "utf8");
    } catch {
      // Ignore persistence errors.
    }
  });
  companionWindow.on("resize", () => {
    if (!companionWindow || companionWindow.isDestroyed()) return;
    try {
      fs.writeFileSync(companionBoundsPath(), JSON.stringify(companionWindow.getBounds(), null, 2), "utf8");
    } catch {
      // Ignore persistence errors.
    }
  });
  companionWindow.on("closed", () => {
    companionWindow = null;
  });
}

function createTray(): void {
  tray = new Tray(path.join(projectRoot, "assets", "tray.png"));
  tray.setToolTip("AURA ASUS");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "Open AURA", click: () => mainWindow?.show() },
      { label: "Show Companion", click: () => createCompanionWindow() },
      { label: "Hide Companion", click: () => companionWindow?.hide() },
      { label: "Restart Backend", click: () => bridge.restart() },
      { type: "separator" },
      { label: "Exit AURA", click: () => {
        isQuitting = true;
        app.quit();
      } },
    ]),
  );
}

app.whenReady().then(() => {
  logStartup("app:ready");
  process.env.AURA_PROVIDER_KEYS_FILE = providerKeysPath();

  session.defaultSession.webRequest.onHeadersReceived(
    { urls: ["*://*.youtube.com/*", "*://*.youtube-nocookie.com/*", "*://*.googlevideo.com/*"] },
    (details, callback) => {
      const responseHeaders = { ...details.responseHeaders };
      delete responseHeaders["x-frame-options"];
      delete responseHeaders["X-Frame-Options"];
      delete responseHeaders["frame-options"];
      delete responseHeaders["content-security-policy"];
      delete responseHeaders["Content-Security-Policy"];
      callback({ cancel: false, responseHeaders });
    }
  );

  createWindow();
  try {
    createTray();
  } catch {
    tray = null;
  }
  globalShortcut.register("CommandOrControl+Space", () => {
    mainWindow?.webContents.send(IPC_CHANNELS.backendEvent, { type: "AURA_COMMAND_OPEN" });
    mainWindow?.show();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  isQuitting = true;
  globalShortcut.unregisterAll();
  bridge.stop();
});

ipcMain.handle(IPC_CHANNELS.request, async (_event, rawRequest) => {
  const request = validateAuraRequest(rawRequest);
  if (request.command === "status") {
    return { backend: bridge.getState() };
  }
  return bridge.request(request.command, request.payload);
});

ipcMain.handle(IPC_CHANNELS.windowMinimize, (event) => {
  const targetWindow = BrowserWindow.fromWebContents(event.sender) || mainWindow;
  targetWindow?.minimize();
});
ipcMain.handle(IPC_CHANNELS.windowMaximize, (event) => {
  const targetWindow = BrowserWindow.fromWebContents(event.sender) || mainWindow;
  if (!targetWindow) {
    return;
  }
  if (targetWindow.isMaximized()) {
    targetWindow.unmaximize();
  } else {
    targetWindow.maximize();
  }
});
ipcMain.handle(IPC_CHANNELS.windowClose, (event) => {
  const targetWindow = BrowserWindow.fromWebContents(event.sender) || mainWindow;
  if (targetWindow && companionWindow && targetWindow.id === companionWindow.id) {
    isQuitting = true;
    app.quit();
    return;
  }
  targetWindow?.close();
});

ipcMain.handle(IPC_CHANNELS.selectFile, async (event) => {
  const targetWindow = BrowserWindow.fromWebContents(event.sender) || mainWindow;
  const options = {
    title: "Select a file for AURA",
    properties: ["openFile"],
    filters: [{ name: "All Files", extensions: ["*"] }],
  } as Electron.OpenDialogOptions;
  const result = targetWindow
    ? await dialog.showOpenDialog(targetWindow, options)
    : await dialog.showOpenDialog(options);
  return result.canceled ? null : result.filePaths[0] || null;
});

ipcMain.handle(IPC_CHANNELS.openPath, async (_event, rawPath) => {
  if (typeof rawPath !== "string" || !rawPath.trim()) {
    throw new Error("openPath requires a file path.");
  }
  const message = await shell.openPath(rawPath);
  return message ? { ok: false, message } : { ok: true };
});

ipcMain.handle(IPC_CHANNELS.systemInfo, async () => ({
  platform: process.platform,
  arch: process.arch,
  totalMemoryGb: Math.round(os.totalmem() / 1024 / 1024 / 1024),
  cpuCount: os.cpus().length,
  hostname: os.hostname(),
  electron: process.versions.electron,
}));

ipcMain.handle(IPC_CHANNELS.loadProviderKeys, async () => {
  try {
    const saved = fs.readFileSync(providerKeysPath(), "utf8");
    const parsed = JSON.parse(saved);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
});

ipcMain.handle(IPC_CHANNELS.saveProviderKeys, async (_event, rawKeys) => {
  const keys = Array.isArray(rawKeys)
    ? rawKeys.map((key) => ({
        id: String((key as { id?: unknown }).id || `key-${Date.now()}`),
        provider: ["groq", "huggingface", "nvidia"].includes(String((key as { provider?: unknown }).provider))
          ? String((key as { provider?: unknown }).provider)
          : "groq",
        label: String((key as { label?: unknown }).label || "API key"),
        value: String((key as { value?: unknown }).value || ""),
        status: ["ready", "limited", "empty"].includes(String((key as { status?: unknown }).status))
          ? String((key as { status?: unknown }).status)
          : "ready",
      }))
    : [];
  fs.mkdirSync(path.dirname(providerKeysPath()), { recursive: true });
  fs.writeFileSync(providerKeysPath(), JSON.stringify(keys, null, 2), "utf8");
  return { ok: true };
});

ipcMain.handle(IPC_CHANNELS.companionShow, async () => {
  createCompanionWindow();
  companionWindow?.show();
  companionWindow?.focus();
});

ipcMain.handle(IPC_CHANNELS.companionHide, async () => {
  companionWindow?.hide();
});

ipcMain.handle(IPC_CHANNELS.selectAudioFiles, async () => {
  if (!mainWindow) {
    return [];
  }
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Select audio files",
    properties: ["openFile", "multiSelections"],
    filters: [
      { name: "Audio", extensions: ["mp3", "wav", "ogg", "m4a", "aac", "flac", "opus"] },
      { name: "All Files", extensions: ["*"] },
    ],
  });
  if (result.canceled) {
    return [];
  }
  return result.filePaths.map((filePath) => ({
    id: Buffer.from(filePath).toString("base64url"),
    title: path.basename(filePath, path.extname(filePath)),
    filePath,
    url: `file://${filePath.replace(/\\/g, "/")}`,
  }));
});

ipcMain.handle(IPC_CHANNELS.openExternal, async (_event, rawUrl) => {
  if (typeof rawUrl !== "string") {
    throw new Error("openExternal requires a URL.");
  }
  const url = new URL(rawUrl);
  if (!["https:", "spotify:", "mailto:"].includes(url.protocol)) {
    throw new Error("Unsupported external URL.");
  }
  await shell.openExternal(url.toString());
  return { ok: true };
});

async function searchYouTube(query: string): Promise<{ ok: boolean; results?: Array<{ id: string; title: string; channel: string; thumbnail: string; duration?: string }>; message?: string }> {
  const clean = String(query || "").trim();
  if (!clean) {
    return { ok: false, message: "Search query is required." };
  }
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    const res = await fetch(`https://www.youtube.com/results?search_query=${encodeURIComponent(clean)}`, {
      headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" },
      signal: controller.signal,
    });
    clearTimeout(timeout);
    const html = await res.text();
    const match = html.match(/var ytInitialData = ({.*?});<\/script>/);
    if (match) {
      const data = JSON.parse(match[1]);
      const contents = data?.contents?.twoColumnSearchResultsRenderer?.primaryContents?.sectionListRenderer?.contents?.[0]?.itemSectionRenderer?.contents || [];
      const videos = contents
        .filter((c: any) => c.videoRenderer && c.videoRenderer.videoId)
        .slice(0, 8)
        .map((c: any) => {
          const v = c.videoRenderer;
          return {
            id: v.videoId,
            title: v.title?.runs?.[0]?.text || "",
            channel: v.ownerText?.runs?.[0]?.text || "",
            thumbnail: v.thumbnail?.thumbnails?.[0]?.url || `https://i.ytimg.com/vi/${v.videoId}/hqdefault.jpg`,
            duration: v.lengthText?.simpleText || "",
          };
        });
      return { ok: true, results: videos };
    }
  } catch (error) {
    logStartup(`youtubeSearchError: ${error instanceof Error ? error.message : String(error)}`);
  }
  return { ok: false, message: "Failed to search YouTube." };
}

let miniYouTubeWindow: BrowserWindow | null = null;

function openMiniYouTubeWindow(videoId?: string, query?: string): void {
  if (miniYouTubeWindow && !miniYouTubeWindow.isDestroyed()) {
    miniYouTubeWindow.focus();
    if (videoId) {
      miniYouTubeWindow.loadURL(`https://www.youtube.com/embed/${videoId}?autoplay=1`);
    } else if (query) {
      miniYouTubeWindow.loadURL(`https://m.youtube.com/results?search_query=${encodeURIComponent(query)}`);
    }
    return;
  }

  miniYouTubeWindow = new BrowserWindow({
    width: 680,
    height: 440,
    minWidth: 380,
    minHeight: 260,
    title: "AURA Mini YouTube",
    alwaysOnTop: true,
    autoHideMenuBar: true,
    backgroundColor: "#0f0f0f",
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
    },
  });

  const targetUrl = videoId
    ? `https://www.youtube.com/embed/${videoId}?autoplay=1`
    : query
    ? `https://m.youtube.com/results?search_query=${encodeURIComponent(query)}`
    : `https://m.youtube.com/`;

  miniYouTubeWindow.loadURL(targetUrl);
  miniYouTubeWindow.on("closed", () => {
    miniYouTubeWindow = null;
  });
}

ipcMain.handle(IPC_CHANNELS.spotifyRequest, async (_event, request) => handleSpotifyRequest(request));
ipcMain.handle(IPC_CHANNELS.youtubeSearch, async (_event, query) => searchYouTube(query));
ipcMain.handle(IPC_CHANNELS.openMiniYouTube, async (_event, payload) => {
  const { videoId, query } = (payload || {}) as { videoId?: string; query?: string };
  openMiniYouTubeWindow(videoId, query);
  return { ok: true };
});
