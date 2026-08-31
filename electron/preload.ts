import { contextBridge, ipcRenderer } from "electron";
import { IPC_CHANNELS } from "./ipcChannels.js";
import { AuraIpcRequest } from "./ipcSchema.js";

contextBridge.exposeInMainWorld("aura", {
  request: (request: AuraIpcRequest) => ipcRenderer.invoke(IPC_CHANNELS.request, request),
  onBackendEvent: (callback: (event: unknown) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, payload: unknown) => callback(payload);
    ipcRenderer.on(IPC_CHANNELS.backendEvent, listener);
    return () => ipcRenderer.removeListener(IPC_CHANNELS.backendEvent, listener);
  },
  window: {
    minimize: () => ipcRenderer.invoke(IPC_CHANNELS.windowMinimize),
    maximize: () => ipcRenderer.invoke(IPC_CHANNELS.windowMaximize),
    close: () => ipcRenderer.invoke(IPC_CHANNELS.windowClose),
  },
  media: {
    selectFile: () => ipcRenderer.invoke(IPC_CHANNELS.selectFile),
    openPath: (filePath: string) => ipcRenderer.invoke(IPC_CHANNELS.openPath, filePath),
    selectAudioFiles: () => ipcRenderer.invoke(IPC_CHANNELS.selectAudioFiles),
    openExternal: (url: string) => ipcRenderer.invoke(IPC_CHANNELS.openExternal, url),
  },
  systemInfo: () => ipcRenderer.invoke(IPC_CHANNELS.systemInfo),
  settings: {
    loadProviderKeys: () => ipcRenderer.invoke(IPC_CHANNELS.loadProviderKeys),
    saveProviderKeys: (keys: unknown) => ipcRenderer.invoke(IPC_CHANNELS.saveProviderKeys, keys),
  },
  companion: {
    show: () => ipcRenderer.invoke(IPC_CHANNELS.companionShow),
    hide: () => ipcRenderer.invoke(IPC_CHANNELS.companionHide),
  },
  spotify: {
    request: (action: string, payload?: unknown) => ipcRenderer.invoke(IPC_CHANNELS.spotifyRequest, { action, payload }),
  },
  youtube: {
    search: (query: string) => ipcRenderer.invoke(IPC_CHANNELS.youtubeSearch, query),
    openMini: (videoId?: string, query?: string) => ipcRenderer.invoke(IPC_CHANNELS.openMiniYouTube, { videoId, query }),
  },
});
