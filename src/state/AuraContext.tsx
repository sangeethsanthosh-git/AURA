import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ActivityRecord, auraApi, BackendState, MemoryRecord, ProviderStatus } from "../services/auraApi";

type AuraRuntime = {
  backend: BackendState;
  providerStatus: ProviderStatus;
  memories: MemoryRecord[];
  activities: ActivityRecord[];
  voiceState: string;
  lastEvent?: unknown;
  refreshRuntime: () => Promise<void>;
};

const AuraContext = createContext<AuraRuntime | null>(null);

export function AuraProvider({ children }: { children: ReactNode }) {
  const [backend, setBackend] = useState<BackendState>("STARTING");
  const [providerStatus, setProviderStatus] = useState<ProviderStatus>({});
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [activities, setActivities] = useState<ActivityRecord[]>([]);
  const [voiceState, setVoiceState] = useState("IDLE");
  const [lastEvent, setLastEvent] = useState<unknown>();

  const refreshRuntime = useCallback(async () => {
    try {
      const [status, providers, memoryItems, activityItems, voice] = await Promise.all([
        auraApi.getStatus(),
        auraApi.getProviderStatus(),
        auraApi.listMemories(),
        auraApi.getActivities(),
        auraApi.getVoiceState(),
      ]);
      setBackend(status.backend);
      setProviderStatus(providers);
      setMemories(memoryItems);
      setActivities(activityItems);
      setVoiceState(voice.state);
    } catch {
      setBackend("OFFLINE");
    }
  }, []);

  useEffect(() => {
    void refreshRuntime();
    return window.aura?.onBackendEvent((event) => {
      setLastEvent(event);
      if (event && typeof event === "object" && "state" in event) {
        setBackend((event as { state: BackendState }).state);
      }
      if (event && typeof event === "object" && (event as { type?: string }).type === "AURA_READY") {
        setBackend("READY");
      }
    });
  }, [refreshRuntime]);

  const value = useMemo(
    () => ({ backend, providerStatus, memories, activities, voiceState, lastEvent, refreshRuntime }),
    [activities, backend, lastEvent, memories, providerStatus, refreshRuntime, voiceState],
  );

  return <AuraContext.Provider value={value}>{children}</AuraContext.Provider>;
}

export function useAuraRuntime(): AuraRuntime {
  const context = useContext(AuraContext);
  if (!context) {
    throw new Error("useAuraRuntime must be used inside AuraProvider.");
  }
  return context;
}
