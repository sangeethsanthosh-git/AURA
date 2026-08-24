export const IPC_CHANNELS = {
  request: "aura:request",
  backendEvent: "aura:backend-event",
  windowMinimize: "aura:window:minimize",
  windowMaximize: "aura:window:maximize",
  windowClose: "aura:window:close",
} as const;

export type IpcChannel = (typeof IPC_CHANNELS)[keyof typeof IPC_CHANNELS];
