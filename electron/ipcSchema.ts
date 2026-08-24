export type AuraCommand =
  | "status"
  | "sendMessage"
  | "listMemories"
  | "forgetMemory"
  | "activities"
  | "providerStatus"
  | "voiceState"
  | "startVoice"
  | "stopVoice";

const COMMANDS = new Set<AuraCommand>([
  "status",
  "sendMessage",
  "listMemories",
  "forgetMemory",
  "activities",
  "providerStatus",
  "voiceState",
  "startVoice",
  "stopVoice",
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
  return request as AuraIpcRequest;
}
