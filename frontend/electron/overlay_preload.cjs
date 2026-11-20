const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronOverlay', {
  showOverlay: () => ipcRenderer.send('show-virtual-hand-overlay'),
  hideOverlay: () => ipcRenderer.send('hide-virtual-hand-overlay'),
  getDisplayBounds: () => ipcRenderer.invoke('get-display-bounds'),
});
