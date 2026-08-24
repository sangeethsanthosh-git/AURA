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
});
