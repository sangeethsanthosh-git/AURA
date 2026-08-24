import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const version = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8")).version;
const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
const outputRoot = process.env.AURA_PORTABLE_OUTPUT || path.join(path.dirname(root), "AURA ASUS EXE");
const appName = `AURA-ASUS-${version}-win-x64-${stamp}`;
const outputDir = path.join(outputRoot, appName);
const resourcesDir = path.join(outputDir, "resources");
const appDir = path.join(resourcesDir, "app");

const electronDist = path.join(root, "node_modules", "electron", "dist");
if (!fs.existsSync(path.join(electronDist, "electron.exe"))) {
  throw new Error("Electron runtime was not found. Run npm install first.");
}

fs.mkdirSync(outputDir, { recursive: true });
fs.cpSync(electronDist, outputDir, { recursive: true });
fs.mkdirSync(appDir, { recursive: true });

const defaultApp = path.join(resourcesDir, "default_app.asar");
if (fs.existsSync(defaultApp)) {
  fs.rmSync(defaultApp);
}

const entries = [
  "dist",
  "dist-electron",
  "backend",
  "ui",
  "app.py",
  "aura_config.py",
  "config.py",
  "conversation_manager.py",
  "language_manager.py",
  "model_router.py",
  "ollama_client.py",
  "speech_manager.py",
  "tts_manager.py",
  "pyproject.toml",
  "uv.lock",
  "package.json",
];

for (const entry of entries) {
  const source = path.join(root, entry);
  if (!fs.existsSync(source)) {
    continue;
  }
  fs.cpSync(source, path.join(appDir, entry), { recursive: true });
}

fs.renameSync(path.join(outputDir, "electron.exe"), path.join(outputDir, "AURA ASUS.exe"));
fs.writeFileSync(path.join(outputRoot, "latest.txt"), outputDir, "utf8");

console.log(`Portable app created: ${outputDir}`);
console.log(`Run: ${path.join(outputDir, "AURA ASUS.exe")}`);
