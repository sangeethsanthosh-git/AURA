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
  startVoice: () => invoke<{ success: boolean; text?: string; error?: string }>("startVoice"),
  stopVoice: () => invoke<{ success: boolean; text?: string; error?: string }>("stopVoice"),
};
