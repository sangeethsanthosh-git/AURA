import { app, BrowserWindow, globalShortcut, ipcMain, nativeTheme, Tray, Menu } from "electron";
import fs from "node:fs";
import path from "node:path";
import { IPC_CHANNELS } from "./ipcChannels.js";
import { validateAuraRequest } from "./ipcSchema.js";
import { PythonBridge } from "./pythonBridge.js";

const isPackagedAsar = __dirname.includes("app.asar");
const projectRoot = isPackagedAsar ? path.join(process.resourcesPath, "app.asar") : path.resolve(__dirname, "..");
const pythonRoot = isPackagedAsar ? path.join(process.resourcesPath, "app.asar.unpacked") : projectRoot;
const startupLog = path.join(pythonRoot, "aura-electron-startup.log");
const bridge = new PythonBridge(projectRoot, pythonRoot);
let mainWindow: InstanceType<typeof BrowserWindow> | null = null;
let tray: InstanceType<typeof Tray> | null = null;

function logStartup(message: string): void {
  try {
    fs.appendFileSync(startupLog, `${new Date().toISOString()} ${message}\n`, "utf8");
  } catch {
    // Logging must never prevent startup.
  }
}

process.on("uncaughtException", (error) => logStartup(`uncaughtException ${error.stack || error.message}`));
process.on("unhandledRejection", (reason) => logStartup(`unhandledRejection ${String(reason)}`));

function createWindow(): void {
  logStartup("createWindow:start");
  mainWindow = new BrowserWindow({
    width: 1240,
    height: 820,
    minWidth: 960,
    minHeight: 680,
    title: "AURA ASUS",
    titleBarStyle: "hidden",
    trafficLightPosition: { x: 16, y: 16 },
    backgroundColor: nativeTheme.shouldUseDarkColors ? "#111315" : "#f4f2ef",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      devTools: true,
    },
  });

  const rendererUrl = process.env.AURA_RENDERER_URL;
  if (rendererUrl) {
    logStartup(`loadURL:${rendererUrl}`);
    mainWindow.loadURL(rendererUrl);
  } else {
    logStartup("loadFile:dist/index.html");
    mainWindow.loadFile(path.join(projectRoot, "dist", "index.html"));
  }

  bridge.on("event", (event) => {
    logStartup(`backendEvent:${JSON.stringify(event)}`);
    mainWindow?.webContents.send(IPC_CHANNELS.backendEvent, event);
  });
  bridge.start();
  logStartup("createWindow:done");
}

function createTray(): void {
  tray = new Tray(path.join(projectRoot, "assets", "tray.png"));
  tray.setToolTip("AURA ASUS");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "Open AURA", click: () => mainWindow?.show() },
      { label: "Restart Backend", click: () => bridge.restart() },
      { type: "separator" },
      { label: "Exit AURA", click: () => app.quit() },
    ]),
  );
}

app.whenReady().then(() => {
  logStartup("app:ready");
  createWindow();
  try {
    createTray();
  } catch {
    tray = null;
  }
  globalShortcut.register("CommandOrControl+Space", () => {
    mainWindow?.webContents.send(IPC_CHANNELS.backendEvent, { type: "AURA_COMMAND_OPEN" });
    mainWindow?.show();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  globalShortcut.unregisterAll();
  bridge.stop();
});

ipcMain.handle(IPC_CHANNELS.request, async (_event, rawRequest) => {
  const request = validateAuraRequest(rawRequest);
  if (request.command === "status") {
    return { backend: bridge.getState() };
  }
  return bridge.request(request.command, request.payload);
});

ipcMain.handle(IPC_CHANNELS.windowMinimize, () => mainWindow?.minimize());
ipcMain.handle(IPC_CHANNELS.windowMaximize, () => {
  if (!mainWindow) {
    return;
  }
  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow.maximize();
  }
});
ipcMain.handle(IPC_CHANNELS.windowClose, () => mainWindow?.close());
