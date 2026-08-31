export type AuraCommand =
  | "status"
  | "sendMessage"
  | "listMemories"
  | "forgetMemory"
  | "activities"
  | "providerStatus"
  | "voiceState"
  | "voiceProfiles"
  | "speakText"
  | "startVoice"
  | "stopVoice"
  | "weatherCurrent"
  | "newsHeadlines"
  | "webSearch";

const COMMANDS = new Set<AuraCommand>([
  "status",
  "sendMessage",
  "listMemories",
  "forgetMemory",
  "activities",
  "providerStatus",
  "voiceState",
  "voiceProfiles",
  "speakText",
  "startVoice",
  "stopVoice",
  "weatherCurrent",
  "newsHeadlines",
  "webSearch",
]);

export interface AuraIpcRequest {
  command: AuraCommand;
  payload?: unknown;
}

export function validateAuraRequest(value: unknown): AuraIpcRequest {
  if (!value || typeof value !== "object") {
    throw new Error("IPC request must be an object.");
  }
  const request = value as Partial<AuraIpcRequest>;
  if (typeof request.command !== "string" || !COMMANDS.has(request.command as AuraCommand)) {
    throw new Error("Unsupported AURA IPC command.");
  }
  if (request.command === "sendMessage") {
    const payload = request.payload as { message?: unknown } | undefined;
    if (!payload || typeof payload.message !== "string" || payload.message.trim().length === 0) {
      throw new Error("sendMessage requires a non-empty message.");
    }
  }
  if (request.command === "forgetMemory") {
    const payload = request.payload as { content?: unknown } | undefined;
    if (!payload || typeof payload.content !== "string" || payload.content.trim().length === 0) {
      throw new Error("forgetMemory requires memory content.");
    }
  }
  if (request.command === "speakText") {
    const payload = request.payload as { text?: unknown; language?: unknown; voice?: unknown } | undefined;
    if (!payload || typeof payload.text !== "string" || payload.text.trim().length === 0) {
      throw new Error("speakText requires non-empty text.");
    }
    if (payload.language !== undefined && typeof payload.language !== "string") {
      throw new Error("speakText language must be a string.");
    }
    if (payload.voice !== undefined && typeof payload.voice !== "string") {
      throw new Error("speakText voice must be a string.");
    }
  }
  if (request.command === "weatherCurrent") {
    const payload = request.payload as { location?: unknown } | undefined;
    if (payload?.location !== undefined && typeof payload.location !== "string") {
      throw new Error("weatherCurrent location must be a string.");
    }
  }
  if (request.command === "webSearch") {
    const payload = request.payload as { query?: unknown; limit?: unknown } | undefined;
    if (!payload || typeof payload.query !== "string" || payload.query.trim().length === 0) {
      throw new Error("webSearch requires a non-empty query.");
    }
    if (payload.limit !== undefined && typeof payload.limit !== "number") {
      throw new Error("webSearch limit must be a number.");
    }
  }
  if (request.command === "newsHeadlines") {
    const payload = request.payload as { category?: unknown; query?: unknown; limit?: unknown } | undefined;
    if (payload?.category !== undefined && typeof payload.category !== "string") {
      throw new Error("newsHeadlines category must be a string.");
    }
    if (payload?.query !== undefined && typeof payload.query !== "string") {
      throw new Error("newsHeadlines query must be a string.");
    }
    if (payload?.limit !== undefined && typeof payload.limit !== "number") {
      throw new Error("newsHeadlines limit must be a number.");
    }
  }
  return request as AuraIpcRequest;
}
