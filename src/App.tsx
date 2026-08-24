import { useState } from "react";
import { AuraProvider } from "./state/AuraContext";
import { AppShell, PageId } from "./components/shell/AppShell";
import { HomePage } from "./pages/HomePage";
import { ChatPage } from "./pages/ChatPage";
import { MemoryPage } from "./pages/MemoryPage";
import { ActivityPage } from "./pages/ActivityPage";
import { SettingsPage } from "./pages/SettingsPage";
import { CapabilityPage } from "./pages/CapabilityPage";

export function App() {
  const [page, setPage] = useState<PageId>("home");

  return (
    <AuraProvider>
      <AppShell page={page} onPageChange={setPage}>
        {page === "home" && <HomePage onOpenChat={() => setPage("chat")} />}
        {page === "chat" && <ChatPage />}
        {page === "tasks" && <CapabilityPage title="Tasks" capability="Task storage is not exposed by the current Python backend." />}
        {page === "knowledge" && <CapabilityPage title="Knowledge" capability="Use chat for RAG and document questions while a dedicated knowledge API is added." />}
        {page === "memory" && <MemoryPage />}
        {page === "activity" && <ActivityPage />}
        {page === "vision" && <CapabilityPage title="Vision" capability="Screen vision is available through chat requests like 'read my screen'." />}
        {page === "voice" && <CapabilityPage title="Voice" capability="Push-to-talk and voice state are exposed. Voice selection requires backend voice profile APIs." />}
        {page === "settings" && <SettingsPage />}
      </AppShell>
    </AuraProvider>
  );
}
