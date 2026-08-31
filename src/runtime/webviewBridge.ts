export {};

import type { AuraIpcRequest } from "../../electron/ipcSchema";

declare global {
  interface Window {
    pywebview?: { api?: Record<string, (...args: unknown[]) => Promise<unknown>> };
  }
}

async function callApi<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`Desktop bridge request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function buildBridge(): NonNullable<Window["aura"]> {
  return {
    request: <T = unknown>(request: AuraIpcRequest) => callApi<T>("/api/desktop/request", { method: "POST", body: JSON.stringify(request) }),
    onBackendEvent: (callback: (event: unknown) => void) => {
      queueMicrotask(() => callback({ type: "AURA_READY" }));
      return () => undefined;
    },
    window: {
      minimize: () => callApi<void>("/api/desktop/window/minimize", { method: "POST", body: "{}" }),
      maximize: () => callApi<void>("/api/desktop/window/maximize", { method: "POST", body: "{}" }),
      close: () => callApi<void>("/api/desktop/window/close", { method: "POST", body: "{}" }),
    },
    media: {
      selectFile: async () => {
        const result = await callApi<{ path?: string | null }>("/api/desktop/media/select-file", { method: "POST", body: "{}" });
        return result.path ?? null;
      },
      openPath: (filePath: string) => callApi<{ ok: boolean; message?: string }>("/api/desktop/media/open-path", { method: "POST", body: JSON.stringify({ filePath }) }),
      selectAudioFiles: () => callApi<Array<{ id: string; title: string; filePath: string; url: string }>>("/api/desktop/media/select-audio-files", { method: "POST", body: "{}" }),
      openExternal: (url: string) => callApi<{ ok: boolean }>("/api/desktop/media/open-external", { method: "POST", body: JSON.stringify({ url }) }),
    },
    systemInfo: () => callApi("/api/desktop/system-info"),
    settings: {
      loadProviderKeys: () => callApi("/api/desktop/settings/provider-keys"),
      saveProviderKeys: (keys: unknown) => callApi<{ ok: boolean }>("/api/desktop/settings/save-provider-keys", { method: "POST", body: JSON.stringify(keys) }),
      loadAppSettings: () => callApi("/api/desktop/settings/app-settings"),
      saveAppSettings: (settings: Record<string, unknown>) => callApi<{ ok: boolean }>("/api/desktop/settings/save-app-settings", { method: "POST", body: JSON.stringify(settings) }),
      installOllama: () => callApi<{ ok: boolean; message?: string }>("/api/desktop/runtime/install-ollama", { method: "POST", body: "{}" }),
    },
    companion: {
      show: () => callApi<void>("/api/desktop/companion/show", { method: "POST", body: "{}" }),
      hide: () => callApi<void>("/api/desktop/companion/hide", { method: "POST", body: "{}" }),
    },
    spotify: {
      request: (action: string, payload?: unknown) => callApi("/api/desktop/spotify/request", { method: "POST", body: JSON.stringify({ action, payload }) }),
    },
    youtube: {
      search: (query: string) => callApi("/api/desktop/youtube/search", { method: "POST", body: JSON.stringify({ query }) }),
      openMini: (videoId?: string, query?: string) => callApi<{ ok: boolean }>("/api/desktop/youtube/open-mini", { method: "POST", body: JSON.stringify({ videoId, query }) }),
    },
  };
}

function attachBridge() {
  if ((window as Window & { aura?: unknown }).aura) {
    return;
  }
  (window as Window & { aura?: ReturnType<typeof buildBridge> }).aura = buildBridge();
}

if (typeof window !== "undefined") {
  attachBridge();
}
