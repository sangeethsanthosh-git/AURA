export interface AppSettings {
  profileName: string;
  assistantName: string;
  age: string;
  dob: string;
  weatherCity: string;
  accountEmail: string;
  reminderEmail: string;
  reminderPhone: string;
  avatarImage: string;
  backgroundImage: string;
  themeMode: "system" | "light" | "dark";
  voiceTone: string;
  defaultModel: string;
  setupComplete: boolean;
}

const SETTINGS_EVENT = "aura:settings-changed";

export function readAppSettings(): AppSettings {
  if (typeof window === "undefined") {
    return defaultSettings();
  }
  return {
    profileName: window.localStorage.getItem("aura:profile-name") || "User",
    assistantName: window.localStorage.getItem("aura:assistant-name") || "AURA",
    age: window.localStorage.getItem("aura:age") || "",
    dob: window.localStorage.getItem("aura:dob") || "",
    weatherCity: window.localStorage.getItem("aura:weather-city") || "Kochi",
    accountEmail: window.localStorage.getItem("aura:account-email") || "",
    reminderEmail: window.localStorage.getItem("aura:reminder-email") || "",
    reminderPhone: window.localStorage.getItem("aura:reminder-phone") || "",
    avatarImage: window.localStorage.getItem("aura:avatar-image") || "",
    backgroundImage: window.localStorage.getItem("aura:background-image") || "",
    themeMode: (window.localStorage.getItem("aura:theme-mode") as AppSettings["themeMode"]) || "system",
    voiceTone: window.localStorage.getItem("aura:voice-tone") || "Neutral",
    defaultModel: window.localStorage.getItem("aura:default-model") || "gemma3:1b",
    setupComplete: window.localStorage.getItem("aura:setup-complete") === "true",
  };
}

export function saveAppSettings(settings: Partial<AppSettings>) {
  if (typeof window === "undefined") {
    return;
  }
  if (settings.profileName !== undefined) window.localStorage.setItem("aura:profile-name", settings.profileName);
  if (settings.assistantName !== undefined) window.localStorage.setItem("aura:assistant-name", settings.assistantName);
  if (settings.age !== undefined) window.localStorage.setItem("aura:age", settings.age);
  if (settings.dob !== undefined) window.localStorage.setItem("aura:dob", settings.dob);
  if (settings.weatherCity !== undefined) window.localStorage.setItem("aura:weather-city", settings.weatherCity);
  if (settings.accountEmail !== undefined) window.localStorage.setItem("aura:account-email", settings.accountEmail);
  if (settings.reminderEmail !== undefined) window.localStorage.setItem("aura:reminder-email", settings.reminderEmail);
  if (settings.reminderPhone !== undefined) window.localStorage.setItem("aura:reminder-phone", settings.reminderPhone);
  if (settings.avatarImage !== undefined) window.localStorage.setItem("aura:avatar-image", settings.avatarImage);
  if (settings.backgroundImage !== undefined) window.localStorage.setItem("aura:background-image", settings.backgroundImage);
  if (settings.themeMode !== undefined) window.localStorage.setItem("aura:theme-mode", settings.themeMode);
  if (settings.voiceTone !== undefined) window.localStorage.setItem("aura:voice-tone", settings.voiceTone);
  if (settings.defaultModel !== undefined) window.localStorage.setItem("aura:default-model", settings.defaultModel);
  if (settings.setupComplete !== undefined) window.localStorage.setItem("aura:setup-complete", String(settings.setupComplete));
  void window.aura?.settings.saveAppSettings?.({ ...readAppSettings() } as Record<string, unknown>).catch(() => undefined);
  window.dispatchEvent(new Event(SETTINGS_EVENT));
}

export async function hydrateAppSettingsFromDesktop() {
  if (typeof window === "undefined") {
    return;
  }
  const loaded = await window.aura?.settings.loadAppSettings?.().catch(() => undefined);
  if (!loaded || typeof loaded !== "object") {
    return;
  }
  if (Object.keys(loaded).length === 0) {
    return;
  }
  writeAppSettingsToLocalStorage({ ...defaultSettings(), ...(loaded as Partial<AppSettings>) });
  window.dispatchEvent(new Event(SETTINGS_EVENT));
}

export function subscribeToAppSettings(listener: () => void) {
  if (typeof window === "undefined") {
    return () => undefined;
  }
  window.addEventListener(SETTINGS_EVENT, listener);
  window.addEventListener("storage", listener);
  return () => {
    window.removeEventListener(SETTINGS_EVENT, listener);
    window.removeEventListener("storage", listener);
  };
}

function defaultSettings(): AppSettings {
  return {
    profileName: "User",
    assistantName: "AURA",
    age: "",
    dob: "",
    weatherCity: "Kochi",
    accountEmail: "",
    reminderEmail: "",
    reminderPhone: "",
    avatarImage: "",
    backgroundImage: "",
    themeMode: "system",
    voiceTone: "Neutral",
    defaultModel: "gemma3:1b",
    setupComplete: false,
  };
}

function writeAppSettingsToLocalStorage(settings: Partial<AppSettings>) {
  if (settings.profileName !== undefined) window.localStorage.setItem("aura:profile-name", String(settings.profileName));
  if (settings.assistantName !== undefined) window.localStorage.setItem("aura:assistant-name", String(settings.assistantName));
  if (settings.age !== undefined) window.localStorage.setItem("aura:age", String(settings.age));
  if (settings.dob !== undefined) window.localStorage.setItem("aura:dob", String(settings.dob));
  if (settings.weatherCity !== undefined) window.localStorage.setItem("aura:weather-city", String(settings.weatherCity));
  if (settings.accountEmail !== undefined) window.localStorage.setItem("aura:account-email", String(settings.accountEmail));
  if (settings.reminderEmail !== undefined) window.localStorage.setItem("aura:reminder-email", String(settings.reminderEmail));
  if (settings.reminderPhone !== undefined) window.localStorage.setItem("aura:reminder-phone", String(settings.reminderPhone));
  if (settings.avatarImage !== undefined) window.localStorage.setItem("aura:avatar-image", String(settings.avatarImage));
  if (settings.backgroundImage !== undefined) window.localStorage.setItem("aura:background-image", String(settings.backgroundImage));
  if (settings.themeMode !== undefined) window.localStorage.setItem("aura:theme-mode", String(settings.themeMode));
  if (settings.voiceTone !== undefined) window.localStorage.setItem("aura:voice-tone", String(settings.voiceTone));
  if (settings.defaultModel !== undefined) window.localStorage.setItem("aura:default-model", String(settings.defaultModel));
  if (settings.setupComplete !== undefined) window.localStorage.setItem("aura:setup-complete", String(settings.setupComplete));
}
