import { useEffect, useState } from "react";
import { AuraProvider } from "./state/AuraContext";
import { AppShell, PageId } from "./components/shell/AppShell";
import { HomePage } from "./pages/HomePage";
import { SetupPage } from "./pages/SetupPage";
import { ExecutiveDashboard } from "./components/dashboard/ExecutiveDashboard";
import { ScheduleCalendarView } from "./components/calendar/ScheduleCalendarView";
import { SettingsPage } from "./pages/SettingsPage";
import { MemoryPage } from "./pages/MemoryPage";
import { ActivityPage } from "./pages/ActivityPage";
import { MusicWidget } from "./components/widgets/MusicWidget";
import { WeatherWidget } from "./components/widgets/WeatherWidget";
import { NewsWidget } from "./components/widgets/NewsWidget";
import { NotificationsWidget } from "./components/widgets/NotificationsWidget";
import { TodayEventsWidget } from "./components/widgets/TodayEventsWidget";
import { YearProgressWidget } from "./components/widgets/YearProgressWidget";
import { AuraCompanionWidget } from "./components/widgets/AuraCompanionWidget";
import { hydrateAppSettingsFromDesktop, readAppSettings, subscribeToAppSettings } from "./state/appSettings";

import { NewsPage } from "./pages/NewsPage";

export function App() {
  const isCompanionWindow =
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).get("companion") === "1";
  const [page, setPage] = useState<PageId>("chat");
  const [sessionKey, setSessionKey] = useState(0);
  const [launchPrompt, setLaunchPrompt] = useState<string | undefined>();
  const [companionVisible, setCompanionVisible] = useState(false);
  const [setupComplete, setSetupComplete] = useState(() => readAppSettings().setupComplete);
  const [settingsHydrated, setSettingsHydrated] = useState(false);

  useEffect(() => subscribeToAppSettings(() => setSetupComplete(readAppSettings().setupComplete)), []);
  useEffect(() => {
    void hydrateAppSettingsFromDesktop().finally(() => {
      setSetupComplete(readAppSettings().setupComplete);
      setSettingsHydrated(true);
    });
  }, []);

  function openPromptInChat(prompt: string) {
    setLaunchPrompt(prompt);
    setPage("chat");
  }

  async function toggleCompanion() {
    if (companionVisible) {
      await window.aura?.companion.hide();
      setCompanionVisible(false);
      return;
    }
    await window.aura?.companion.show();
    setCompanionVisible(true);
  }

  if (isCompanionWindow) {
    return (
      <AuraProvider>
        <div className="companion-window-root" aria-label="AURA desktop companion">
          <AuraCompanionWidget />
        </div>
      </AuraProvider>
    );
  }

  if (!settingsHydrated) {
    return null;
  }

  if (!setupComplete) {
    return (
      <AuraProvider>
        <SetupPage onComplete={() => setSetupComplete(true)} />
      </AuraProvider>
    );
  }

  return (
    <AuraProvider>
      <AppShell
        activePage={page}
        onPageChange={setPage}
        companionVisible={companionVisible}
        onToggleCompanion={() => void toggleCompanion()}
        onNewSession={() => {
          setPage("chat");
          setLaunchPrompt(undefined);
          setSessionKey((prev) => prev + 1);
        }}
      >
        {/* Module 1: Studio & Deep Research (Places, Document Report, Sources) */}
        {page === "chat" && (
          <HomePage
            key={`${sessionKey}-${launchPrompt || "studio"}`}
            initialPrompt={launchPrompt}
            onOpenChat={() => setPage("chat")}
          />
        )}

        {/* Module 2: Executive Productivity Dashboard */}
        {page === "dashboard" && (
          <ExecutiveDashboard
            onTriggerPrompt={(p) => {
              openPromptInChat(p);
            }}
          />
        )}

        {/* Module 3: Schedule & Calendar Suite */}
        {page === "schedule" && <ScheduleCalendarView />}

        {/* Module 4: Dedicated News & Editorial Journal */}
        {page === "news" && <NewsPage />}

        {/* Module 5: Media & Tools with Minimalist Reference Widgets */}
        {page === "widgets" && (
          <div className="widgets-studio-page">
            <div className="widgets-studio-grid">
              <section className="widgets-studio-tile widgets-studio-tile--music">
                <MusicWidget />
              </section>
              <section className="widgets-studio-tile widgets-studio-tile--weather">
                <WeatherWidget />
              </section>
              <section className="widgets-studio-tile widgets-studio-tile--events">
                <TodayEventsWidget />
              </section>
              <section className="widgets-studio-tile widgets-studio-tile--year">
                <YearProgressWidget />
              </section>
              <section className="widgets-studio-tile widgets-studio-tile--notifications">
                <NotificationsWidget />
              </section>
              <section className="widgets-studio-tile widgets-studio-tile--news">
                <NewsWidget onViewMore={() => setPage("news")} />
              </section>
            </div>
          </div>
        )}

        {/* Module 6: Memory */}
        {page === "memory" && <MemoryPage />}

        {/* Module 7: Activity History */}
        {page === "activity" && <ActivityPage />}

        {/* Module 8: Settings & Models */}
        {page === "settings" && <SettingsPage />}
      </AppShell>
    </AuraProvider>
  );
}
