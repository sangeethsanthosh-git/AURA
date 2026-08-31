/// <reference types="vite/client" />

import type { AuraIpcRequest } from "../electron/ipcSchema";

declare global {
  interface Window {
    pywebview?: {
      api?: Record<string, (...args: unknown[]) => Promise<unknown>>;
    };
    aura?: {
      request<T = unknown>(request: AuraIpcRequest): Promise<T>;
      onBackendEvent(callback: (event: unknown) => void): () => void;
      window: {
        minimize(): Promise<void>;
        maximize(): Promise<void>;
        close(): Promise<void>;
      };
      media: {
        selectFile(): Promise<string | null>;
        openPath(filePath: string): Promise<{ ok: boolean; message?: string }>;
        selectAudioFiles(): Promise<Array<{ id: string; title: string; filePath: string; url: string }>>;
        openExternal(url: string): Promise<{ ok: boolean }>;
      };
      systemInfo(): Promise<{
        platform: string;
        arch: string;
        totalMemoryGb: number;
        cpuCount: number;
        hostname: string;
        electron: string;
      }>;
      settings: {
        loadProviderKeys(): Promise<Array<{ id: string; provider: "groq" | "huggingface" | "nvidia"; label: string; value: string; status: "ready" | "limited" | "empty" }>>;
        saveProviderKeys(keys: Array<{ id: string; provider: "groq" | "huggingface" | "nvidia"; label: string; value: string; status: "ready" | "limited" | "empty" }>): Promise<{ ok: boolean }>;
        loadAppSettings?(): Promise<Record<string, unknown>>;
        saveAppSettings?(settings: Record<string, unknown>): Promise<{ ok: boolean }>;
        installOllama?(): Promise<{ ok: boolean; message?: string }>;
      };
      companion: {
        show(): Promise<void>;
        hide(): Promise<void>;
      };
      spotify: {
        request<T = unknown>(action: string, payload?: unknown): Promise<T>;
      };
      youtube?: {
        search(query: string): Promise<{ ok: boolean; results?: Array<{ id: string; title: string; channel: string; thumbnail: string; duration?: string }> }>;
        openMini?(videoId?: string, query?: string): Promise<{ ok: boolean }>;
      };
    };
  }
}
