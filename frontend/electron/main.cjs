const { app, BrowserWindow, Tray, Menu, globalShortcut, nativeImage, ipcMain, shell, session } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { spawn } = require('child_process');

// Optimize Chromium renderer flags for desktop smoothness
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-zero-copy');
app.commandLine.appendSwitch('disable-background-timer-throttling');

let mainWindow = null;
let tray = null;
let isQuitting = false;
let backendProcess = null;
let ollamaProcess = null;

function findProjectRoot() {
  const candidates = [
    path.resolve(__dirname, '../../'),
    path.resolve(process.resourcesPath || '', '../../'),
    path.resolve(process.resourcesPath || '', '../../../../'),
    path.dirname(process.execPath),
    path.resolve(path.dirname(process.execPath), '../../'),
    process.cwd(),
  ];

  for (const dir of candidates) {
    if (dir && (fs.existsSync(path.join(dir, '.venv')) || fs.existsSync(path.join(dir, 'backend')))) {
      return dir;
    }
  }
  return path.resolve(__dirname, '../../');
}

const projectRoot = findProjectRoot();

// Ensure single instance
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      if (!mainWindow.isVisible()) mainWindow.show();
      mainWindow.focus();
      mainWindow.setAlwaysOnTop(true);
      mainWindow.setAlwaysOnTop(false);
    }
  });
}

function checkServiceUrl(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      resolve(res.statusCode >= 200 && res.statusCode < 400);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(1200, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function ensureBackgroundServices() {
  // 1. Verify Ollama LLM Service
  try {
    const isOllamaUp = await checkServiceUrl('http://127.0.0.1:11434/api/tags');
    if (!isOllamaUp) {
      const ollamaExe = path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Ollama', 'ollama.exe');
      if (fs.existsSync(ollamaExe)) {
        ollamaProcess = spawn(ollamaExe, ['serve'], {
          windowsHide: true,
          detached: true,
          stdio: 'ignore',
        });
        console.log('Spawned background Ollama daemon.');
      }
    }
  } catch (err) {
    console.debug('Ollama auto-check note:', err);
  }

  // 2. Verify FastAPI Backend Service
  try {
    const isBackendUp = await checkServiceUrl('http://127.0.0.1:8000/health');
    if (!isBackendUp) {
      const pythonExe = path.join(projectRoot, '.venv', 'Scripts', 'python.exe');
      if (fs.existsSync(pythonExe)) {
        backendProcess = spawn(
          pythonExe,
          ['-m', 'uvicorn', 'backend.api.app:app', '--host', '127.0.0.1', '--port', '8000'],
          {
            cwd: projectRoot,
            windowsHide: true,
            stdio: 'ignore',
          }
        );
        console.log('Spawned background Python FastAPI service.');
      }
    }
  } catch (err) {
    console.debug('Backend auto-check note:', err);
  }
}

function createTray() {
  const iconPng = path.join(__dirname, 'icon.png');
  const trayIcon = path.join(__dirname, 'tray_icon.png');
  let icon;
  if (fs.existsSync(trayIcon)) {
    icon = nativeImage.createFromPath(trayIcon);
  } else if (fs.existsSync(iconPng)) {
    icon = nativeImage.createFromPath(iconPng);
  } else {
    icon = nativeImage.createEmpty();
  }

  tray = new Tray(icon);
  tray.setToolTip('AURA · AI Voice & Desktop Assistant');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show AURA',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    {
      label: 'Push to Talk (Ctrl+Shift+Space)',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
          mainWindow.webContents.send('global-hotkey', { action: 'toggle-listen' });
        }
      },
    },
    {
      label: 'Toggle Wake Word',
      click: () => {
        if (mainWindow) {
          mainWindow.webContents.send('global-hotkey', { action: 'toggle-wake-word' });
        }
      },
    },
    { type: 'separator' },
    {
      label: 'Hide to Tray',
      click: () => {
        if (mainWindow) {
          mainWindow.hide();
        }
      },
    },
    { type: 'separator' },
    {
      label: 'Quit AURA',
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    if (!mainWindow) return;
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

function registerGlobalShortcuts() {
  const primaryKey = 'CommandOrControl+Shift+Space';
  const fallbackKey = 'Alt+A';

  const triggerPTT = () => {
    if (!mainWindow) return;
    if (!mainWindow.isVisible()) {
      mainWindow.show();
    }
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }
    mainWindow.focus();
    mainWindow.webContents.send('global-hotkey', { action: 'toggle-listen', source: 'global_shortcut' });
  };

  try {
    const success1 = globalShortcut.register(primaryKey, triggerPTT);
    if (success1) {
      console.log(`Global hotkey registered: ${primaryKey}`);
    }

    const success2 = globalShortcut.register(fallbackKey, triggerPTT);
    if (success2) {
      console.log(`Fallback global hotkey registered: ${fallbackKey}`);
    }
  } catch (err) {
    console.error('Error registering global shortcuts:', err);
  }
}

function isSafeExternalUrl(rawUrl) {
  if (!rawUrl || typeof rawUrl !== 'string') return false;
  const trimmed = rawUrl.trim();
  try {
    const parsed = new URL(trimmed);
    const protocol = parsed.protocol.toLowerCase();
    const safeProtocols = ['https:', 'http:', 'spotify:', 'discord:', 'steam:', 'mailto:', 'ms-settings:'];
    if (!safeProtocols.includes(protocol)) {
      console.warn(`[Electron Sandbox] Blocked unsafe external URL protocol: ${protocol} (${trimmed})`);
      return false;
    }
    return true;
  } catch {
    const schemeMatch = trimmed.match(/^([a-zA-Z0-9+.-]+):/);
    if (schemeMatch) {
      const scheme = schemeMatch[1].toLowerCase() + ':';
      const safeProtocols = ['spotify:', 'discord:', 'steam:', 'mailto:', 'ms-settings:'];
      return safeProtocols.includes(scheme);
    }
    return false;
  }
}

function setupContentSecurityPolicy() {
  if (!session.defaultSession) return;
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const csp = [
      "default-src 'self' 'unsafe-inline' 'unsafe-eval' file: http://127.0.0.1:8000 ws://127.0.0.1:8000 http://localhost:5173 ws://localhost:5173 data: blob: https://en.wikipedia.org https://upload.wikimedia.org;",
      "img-src 'self' file: http://127.0.0.1:8000 http://localhost:5173 data: blob: https:;",
      "media-src 'self' file: http://127.0.0.1:8000 http://localhost:5173 data: blob:;",
      "connect-src 'self' http://127.0.0.1:8000 ws://127.0.0.1:8000 http://localhost:5173 ws://localhost:5173 https://en.wikipedia.org https://upload.wikimedia.org;"
    ].join(' ');

    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [csp],
        'X-Content-Type-Options': ['nosniff'],
        'X-Frame-Options': ['DENY'],
      },
    });
  });
}

function createWindow() {
  const iconPng = path.join(__dirname, 'icon.png');
  mainWindow = new BrowserWindow({
    width: 1220,
    height: 840,
    minWidth: 860,
    minHeight: 620,
    title: 'AURA · AI Chat & Voice Assistant',
    icon: fs.existsSync(iconPng) ? iconPng : undefined,
    backgroundColor: '#FBF8F5',
    autoHideMenuBar: true,
    show: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      backgroundThrottling: false, // Keep companion responsive
    },
  });

  mainWindow.webContents.on('console-message', (_event, level, message, line, sourceId) => {
    console.log(`[Renderer ${level}] ${message} (${sourceId}:${line})`);
  });

  mainWindow.webContents.on('did-fail-load', (_event, errorCode, errorDescription, validatedURL) => {
    console.error(`[Load Fail] ${errorCode}: ${errorDescription} (${validatedURL})`);
  });

  const distPath = path.join(__dirname, '../dist/index.html');

  if (process.env.ELECTRON_DEV === 'true') {
    mainWindow.loadURL('http://localhost:5173');
  } else if (fs.existsSync(distPath)) {
    mainWindow.loadFile(distPath);
  } else {
    mainWindow.loadURL('http://127.0.0.1:8000');
  }

  // Force window to appear visibly on screen immediately
  mainWindow.center();
  mainWindow.show();
  mainWindow.focus();

  mainWindow.once('ready-to-show', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  // Safety fallback: ensure visibility within 300ms
  setTimeout(() => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.show();
      mainWindow.focus();
    }
  }, 300);

  // Keep external links out of the desktop assistant window (enforcing Sandbox Protocol)
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isSafeExternalUrl(url)) {
      shell.openExternal(url);
    } else {
      console.warn(`[Electron Sandbox] Blocked unsafe external window request: ${url}`);
    }
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    const isAppOrigin = url.startsWith('file://') || url.includes('localhost:5173') || url.includes('127.0.0.1:8000');
    if (!isAppOrigin) {
      event.preventDefault();
      if (isSafeExternalUrl(url)) {
        shell.openExternal(url);
      } else {
        console.warn(`[Electron Sandbox] Blocked unsafe navigation: ${url}`);
      }
    }
  });

  // Intercept close button: minimize to tray instead of quitting
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
      if (tray && process.platform === 'win32') {
        tray.displayBalloon({
          title: 'AURA Assistant',
          content: 'AURA is running in the background. Press Ctrl+Shift+Space to summon anytime.',
        });
      }
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  createTray();
  registerGlobalShortcuts();
}

let virtualHandOverlay = null;

function getVirtualDesktopBounds() {
  const { screen } = require('electron');
  const displays = screen.getAllDisplays();
  let minX = 0, minY = 0, maxX = 0, maxY = 0;
  for (const d of displays) {
    minX = Math.min(minX, d.bounds.x);
    minY = Math.min(minY, d.bounds.y);
    maxX = Math.max(maxX, d.bounds.x + d.bounds.width);
    maxY = Math.max(maxY, d.bounds.y + d.bounds.height);
  }
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}

function createVirtualHandOverlay() {
  const bounds = getVirtualDesktopBounds();

  virtualHandOverlay = new BrowserWindow({
    x: bounds.x,
    y: bounds.y,
    width: bounds.width,
    height: bounds.height,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    hasShadow: false,
    focusable: false,
    resizable: false,
    show: false, // Initially hidden; shows during desktop automation
    webPreferences: {
      preload: path.join(__dirname, 'overlay_preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
  });

  virtualHandOverlay.setIgnoreMouseEvents(true, { forward: true });
  virtualHandOverlay.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  virtualHandOverlay.setAlwaysOnTop(true, 'screen-saver');

  const overlayHtml = path.join(__dirname, 'virtual_hand_overlay.html');
  virtualHandOverlay.loadFile(overlayHtml);

  virtualHandOverlay.on('closed', () => {
    virtualHandOverlay = null;
  });
}

// IPC Handlers
ipcMain.on('show-virtual-hand-overlay', () => {
  if (virtualHandOverlay) {
    virtualHandOverlay.showInactive();
  }
});

ipcMain.on('hide-virtual-hand-overlay', () => {
  if (virtualHandOverlay && virtualHandOverlay.isVisible()) {
    virtualHandOverlay.hide();
  }
});

ipcMain.handle('get-display-bounds', () => {
  return getVirtualDesktopBounds();
});

ipcMain.on('tray-balloon', (_event, payload) => {
  if (tray && process.platform === 'win32') {
    const title = typeof payload?.title === 'string' ? payload.title.slice(0, 100) : 'AURA';
    const content = typeof payload?.content === 'string' ? payload.content.slice(0, 300) : '';
    tray.displayBalloon({ title, content });
  }
});

ipcMain.on('show-window', () => {
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  }
});

ipcMain.on('hide-window', () => {
  if (mainWindow) {
    mainWindow.hide();
  }
});

app.whenReady().then(() => {
  // 1. Enforce Electron Content Security Policy & Sandbox Protections
  setupContentSecurityPolicy();
  // 2. Create desktop window immediately without blocking
  createWindow();
  // 3. Create independent transparent virtual hand desktop overlay (initially hidden)
  createVirtualHandOverlay();
  // 4. Ensure background AI and FastAPI services in parallel
  ensureBackgroundServices().catch((err) => {
    console.debug('Background service auto-check completed:', err);
  });
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  if (tray) {
    tray.destroy();
  }
  if (backendProcess) {
    try {
      backendProcess.kill();
    } catch {}
  }
  if (ollamaProcess) {
    try {
      ollamaProcess.kill();
    } catch {}
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin' && isQuitting) {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  } else if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  }
});
