export const IPC_CHANNELS = {
  request: "aura:request",
  backendEvent: "aura:backend-event",
  windowMinimize: "aura:window:minimize",
  windowMaximize: "aura:window:maximize",
  windowClose: "aura:window:close",
  selectFile: "aura:shell:select-file",
  openPath: "aura:shell:open-path",
  loadProviderKeys: "aura:settings:load-provider-keys",
  saveProviderKeys: "aura:settings:save-provider-keys",
  companionShow: "aura:companion:show",
  companionHide: "aura:companion:hide",
  selectAudioFiles: "aura:media:select-audio-files",
  openExternal: "aura:shell:open-external",
  systemInfo: "aura:system-info",
  spotifyRequest: "aura:spotify:request",
  youtubeSearch: "aura:youtube:search",
  openMiniYouTube: "aura:youtube:open-mini",
} as const;

export type IpcChannel = (typeof IPC_CHANNELS)[keyof typeof IPC_CHANNELS];
