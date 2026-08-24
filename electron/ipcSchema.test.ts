import { describe, expect, it } from "vitest";
import { validateAuraRequest } from "./ipcSchema.js";

describe("IPC schema", () => {
  it("accepts known typed commands", () => {
    expect(validateAuraRequest({ command: "sendMessage", payload: { message: "hello" } }).command).toBe("sendMessage");
  });

  it("rejects arbitrary commands", () => {
    expect(() => validateAuraRequest({ command: "shell", payload: { cmd: "dir" } })).toThrow("Unsupported");
  });

  it("requires validated payloads", () => {
    expect(() => validateAuraRequest({ command: "sendMessage", payload: { message: "" } })).toThrow("non-empty");
  });
});
