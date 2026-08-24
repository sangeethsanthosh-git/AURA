import { ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { EventEmitter } from "node:events";
import { AuraCommand } from "./ipcSchema.js";

type PendingRequest = {
  resolve: (value: unknown) => void;
  reject: (reason: Error) => void;
  timer: NodeJS.Timeout;
};

export type BackendState = "STARTING" | "READY" | "DEGRADED" | "OFFLINE" | "ERROR";

export class PythonBridge extends EventEmitter {
  private process: ChildProcessWithoutNullStreams | null = null;
  private pending = new Map<string, PendingRequest>();
  private nextId = 1;
  private state: BackendState = "OFFLINE";
  private readonly projectRoot: string;
  private readonly pythonRoot: string;

  constructor(projectRoot: string, pythonRoot = projectRoot) {
    super();
    this.projectRoot = projectRoot;
    this.pythonRoot = pythonRoot;
  }

  getState(): BackendState {
    return this.state;
  }

  start(): void {
    if (this.process) {
      return;
    }
    this.setState("STARTING");
    const scriptPath = path.join(this.pythonRoot, "backend", "electron_bridge.py");
    const pythonExecutable = this.resolvePythonExecutable();
    this.process = spawn(pythonExecutable, [scriptPath], {
      cwd: this.pythonRoot,
      env: { ...process.env, PYTHONUTF8: "1", AURA_APP_ROOT: this.pythonRoot },
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });

    const stdout = readline.createInterface({ input: this.process.stdout });
    stdout.on("line", (line) => this.handleLine(line));
    this.process.stderr.on("data", (chunk) => {
      const message = chunk.toString("utf8").trim();
      if (message.includes("ERROR") || message.includes("Traceback")) {
        this.emit("event", { type: "AURA_ERROR", message });
      }
    });
    this.process.on("exit", () => {
      this.process = null;
      this.rejectAll(new Error("AURA backend process exited."));
      this.setState("OFFLINE");
    });
    this.process.on("error", (error) => {
      this.rejectAll(error);
      this.setState("ERROR");
    });
  }

  stop(): void {
    if (!this.process) {
      return;
    }
    this.process.kill();
    this.process = null;
    this.rejectAll(new Error("AURA backend process stopped."));
    this.setState("OFFLINE");
  }

  restart(): void {
    this.stop();
    this.start();
  }

  request(command: AuraCommand, payload?: unknown): Promise<unknown> {
    if (!this.process || !this.process.stdin.writable) {
      this.start();
    }
    if (!this.process || !this.process.stdin.writable) {
      return Promise.reject(new Error("AURA backend is offline."));
    }
    const id = String(this.nextId++);
    const message = JSON.stringify({ id, command, payload }) + "\n";
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error("AURA backend request timed out."));
      }, 120000);
      this.pending.set(id, { resolve, reject, timer });
      this.process?.stdin.write(message, "utf8");
    });
  }

  private handleLine(line: string): void {
    if (!line.trim()) {
      return;
    }
    let message: { id?: string; ok?: boolean; result?: unknown; error?: string; event?: unknown };
    try {
      message = JSON.parse(line);
    } catch {
      this.emit("event", { type: "AURA_ERROR", message: "Received malformed backend message." });
      return;
    }
    if (message.event) {
      this.emit("event", message.event);
      if ((message.event as { type?: string }).type === "AURA_READY") {
        this.setState("READY");
      }
      return;
    }
    if (!message.id) {
      return;
    }
    const pending = this.pending.get(message.id);
    if (!pending) {
      return;
    }
    this.pending.delete(message.id);
    clearTimeout(pending.timer);
    if (message.ok) {
      pending.resolve(message.result);
    } else {
      pending.reject(new Error(message.error || "AURA backend request failed."));
    }
  }

  private rejectAll(error: Error): void {
    for (const [id, pending] of this.pending.entries()) {
      clearTimeout(pending.timer);
      pending.reject(error);
      this.pending.delete(id);
    }
  }

  private setState(state: BackendState): void {
    this.state = state;
    this.emit("event", { type: "AURA_BACKEND_STATE", state });
  }

  private resolvePythonExecutable(): string {
    const candidates = [
      process.env.AURA_PYTHON,
      process.env.PYTHON,
      process.env.VIRTUAL_ENV ? path.join(process.env.VIRTUAL_ENV, "Scripts", "python.exe") : undefined,
      path.join(this.pythonRoot, ".venv", "Scripts", "python.exe"),
      path.join(this.pythonRoot, "venv", "Scripts", "python.exe"),
      "python",
    ];
    for (const candidate of candidates) {
      if (!candidate) {
        continue;
      }
      if (candidate === "python" || fs.existsSync(candidate)) {
        return candidate;
      }
    }
    return "python";
  }
}
