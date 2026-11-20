const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  platform: process.platform,
  onGlobalHotkey: (callback) => {
    ipcRenderer.on('global-hotkey', (_event, data) => callback(data));
  },
  showWindow: () => ipcRenderer.send('show-window'),
  hideWindow: () => ipcRenderer.send('hide-window'),
  showBalloon: (title, content) => ipcRenderer.send('tray-balloon', { title, content }),
});
