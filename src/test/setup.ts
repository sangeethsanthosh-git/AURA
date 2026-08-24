import "@testing-library/jest-dom/vitest";

Object.defineProperty(window, "aura", {
  configurable: true,
  value: {
    request: async ({ command }: { command: string }) => {
      if (command === "status") {
        return { backend: "READY" };
      }
      if (command === "providerStatus") {
        return { Application: "Ready", TTS: "Disabled" };
      }
      if (command === "listMemories") {
        return [];
      }
      if (command === "activities") {
        return [];
      }
      if (command === "voiceState") {
        return { state: "IDLE" };
      }
      return {};
    },
    onBackendEvent: () => () => undefined,
    window: {
      minimize: async () => undefined,
      maximize: async () => undefined,
      close: async () => undefined,
    },
  },
});
