/// <reference types="vite/client" />

import type { AuraIpcRequest } from "../electron/ipcSchema";

declare global {
  interface Window {
    aura?: {
      request<T = unknown>(request: AuraIpcRequest): Promise<T>;
      onBackendEvent(callback: (event: unknown) => void): () => void;
      window: {
        minimize(): Promise<void>;
        maximize(): Promise<void>;
        close(): Promise<void>;
      };
    };
  }
}
