import { describe, expect, it } from "vitest";
import { validateAuraRequest } from "./ipcSchema.js";

describe("IPC schema", () => {
  it("accepts known typed commands", () => {
    expect(validateAuraRequest({ command: "sendMessage", payload: { message: "hello" } }).command).toBe("sendMessage");
    expect(validateAuraRequest({ command: "providerStatus" }).command).toBe("providerStatus");
    expect(validateAuraRequest({ command: "weatherCurrent", payload: { location: "Kochi" } }).command).toBe("weatherCurrent");
    expect(validateAuraRequest({ command: "newsHeadlines", payload: { category: "Technology", query: "AI", limit: 8 } }).command).toBe("newsHeadlines");
  });

  it("rejects arbitrary commands", () => {
    expect(() => validateAuraRequest({ command: "shell", payload: { cmd: "dir" } })).toThrow("Unsupported");
  });

  it("requires validated payloads", () => {
    expect(() => validateAuraRequest({ command: "sendMessage", payload: { message: "" } })).toThrow("non-empty");
  });
});
