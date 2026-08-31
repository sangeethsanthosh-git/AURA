import "@testing-library/jest-dom/vitest";

let testMemories: Array<{
  id: string;
  category: string;
  content: string;
  status: string;
  importance: number;
  updated_at: string;
}> = [];

Object.defineProperty(window, "aura", {
  configurable: true,
  value: {
    request: async ({ command, payload }: { command: string; payload?: Record<string, unknown> }) => {
      if (command === "status") {
        return { backend: "READY" };
      }
      if (command === "providerStatus") {
        return { Application: "Ready", TTS: "Disabled" };
      }
      if (command === "listMemories") {
        return testMemories;
      }
      if (command === "sendMessage") {
        const message = String(payload?.message || "");
        const memory = message.replace(/^remember\s+/i, "").trim();
        if (memory) {
          testMemories = [
            {
              id: `memory-${testMemories.length + 1}`,
              category: "preferences",
              content: memory,
              status: "ACTIVE",
              importance: 0.92,
              updated_at: "2026-08-27T00:00:00.000Z",
            },
            ...testMemories,
          ];
        }
        return { text: "I will remember that.", success: true, intent: "Memory", execution_source: "MemoryManager", llm_provider: "None", model: "None", execution_time: 0, metadata: {} };
      }
      if (command === "forgetMemory") {
        const content = String(payload?.content || "");
        testMemories = testMemories.filter((memory) => memory.content !== content);
        return { text: "Forgotten.", success: true, intent: "Memory", execution_source: "MemoryManager", llm_provider: "None", model: "None", execution_time: 0, metadata: {} };
      }
      if (command === "activities") {
        return [];
      }
      if (command === "voiceState") {
        return { state: "IDLE" };
      }
      if (command === "weatherCurrent") {
        return {
          ok: true,
          data: {
            location: { name: "Kochi", state: "Kerala", country: "India" },
            formatted_weather: {
              temperature: 29,
              condition: "Partly cloudy",
              humidity: 78,
              wind_speed: 12,
              feels_like: 32,
              message: "Weather for Kochi",
            },
          },
        };
      }
      if (command === "newsHeadlines") {
        return {
          ok: true,
          data: {
            category: "All",
            query: "",
            source: "Public RSS feeds",
            articles: [
              {
                id: "test-news-1",
                title: "AURA routes local actions without cloud APIs",
                excerpt: "Memory and system control stay local while external providers handle their own tasks.",
                url: "https://example.com/aura-news",
                source: "AURA Test Feed",
                category: "Technology",
                published_at: "Thu, 27 Aug 2026 12:00:00 GMT",
              },
            ],
          },
        };
      }
      return {};
    },
    onBackendEvent: () => () => undefined,
    window: {
      minimize: async () => undefined,
      maximize: async () => undefined,
      close: async () => undefined,
    },
    media: {
      selectFile: async () => null,
      openPath: async () => ({ ok: true }),
      selectAudioFiles: async () => [],
      openExternal: async () => ({ ok: true }),
    },
    settings: {
      loadProviderKeys: async () => [],
      saveProviderKeys: async () => ({ ok: true }),
    },
    companion: {
      show: async () => undefined,
      hide: async () => undefined,
    },
  },
});
