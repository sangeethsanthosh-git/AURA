import { FormEvent, useEffect, useState } from "react";
import { auraApi } from "../../services/auraApi";
import { readAppSettings, subscribeToAppSettings } from "../../state/appSettings";

interface HourlyItem {
  timeLabel: string;
  icon: string;
  temp: number;
}

interface WeatherData {
  temp: number;
  condition: string;
  city: string;
  icon: string;
  humidity?: number;
  windSpeed?: number;
  feelsLike?: number;
  hourly: HourlyItem[];
}

function iconForCondition(condition: string): string {
  const lowered = condition.toLowerCase();
  if (lowered.includes("clear")) return "Sun";
  if (lowered.includes("cloud") || lowered.includes("overcast")) return "Cloud";
  if (lowered.includes("fog")) return "Fog";
  if (lowered.includes("thunder")) return "Storm";
  if (lowered.includes("snow")) return "Snow";
  return "Rain";
}

function fallbackHourly(weather: WeatherData): HourlyItem[] {
  return Array.from({ length: 6 }, (_, index) => ({
    timeLabel: index === 0 ? "Now" : `+${index}h`,
    icon: weather.icon,
    temp: weather.temp,
  }));
}

interface WeatherWidgetProps {
  initialTheme?: "light" | "dark";
  defaultCity?: string;
}

export function WeatherWidget({ initialTheme = "light", defaultCity }: WeatherWidgetProps) {
  const [theme, setTheme] = useState<"light" | "dark">(initialTheme);
  const [cityInput, setCityInput] = useState(defaultCity || readAppSettings().weatherCity || "");
  const [isSearching, setIsSearching] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [weather, setWeather] = useState<WeatherData>({
    temp: 0,
    condition: "Loading",
    city: "Current location",
    icon: "Cloud",
    hourly: [],
  });

  async function fetchWeatherForCity(cityName?: string) {
    setLoading(true);
    setError("");
    try {
      const response = await auraApi.getWeather(cityName?.trim() || undefined);
      if (!response.ok) {
        throw new Error(response.error?.message || "Weather is unavailable.");
      }

      const formatted = response.data.formatted_weather || {};
      const location = response.data.location || {};
      const city = [location.name, location.state, location.country].filter(Boolean).join(", ") || cityName || "Current location";
      const condition = formatted.condition || "Unknown";
      const nextWeather: WeatherData = {
        temp: Math.round(Number(formatted.temperature ?? 0)),
        condition,
        city,
        icon: iconForCondition(condition),
        humidity: formatted.humidity,
        windSpeed: formatted.wind_speed,
        feelsLike: formatted.feels_like,
        hourly: [],
      };
      nextWeather.hourly = fallbackHourly(nextWeather);
      setWeather(nextWeather);
      setCityInput(cityName || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Weather is unavailable.");
    } finally {
      setLoading(false);
      setIsSearching(false);
    }
  }

  useEffect(() => {
    void fetchWeatherForCity(defaultCity);
  }, [defaultCity]);

  useEffect(() => subscribeToAppSettings(() => {
    const nextCity = readAppSettings().weatherCity || "";
    if (!cityInput.trim()) {
      setCityInput(nextCity);
      void fetchWeatherForCity(nextCity);
    }
  }), [cityInput]);

  function handleSearchSubmit(event: FormEvent) {
    event.preventDefault();
    if (!cityInput.trim()) {
      void fetchWeatherForCity();
      return;
    }
    void fetchWeatherForCity(cityInput);
  }

  return (
    <div className={`minimal-weather-card minimal-weather-card--${theme}`} aria-label="Current Weather Widget">
      <div className="weather-card-controls-overlay">
        <button
          type="button"
          className="weather-theme-toggle-btn"
          onClick={() => setTheme((prev) => (prev === "light" ? "dark" : "light"))}
          title={`Switch to ${theme === "light" ? "Dark" : "Light"} mode`}
        >
          {theme === "light" ? "Dark" : "Light"}
        </button>
        <button type="button" className="weather-search-toggle-btn" onClick={() => setIsSearching(!isSearching)} title="Search place">
          Search
        </button>
      </div>

      {isSearching && (
        <form onSubmit={handleSearchSubmit} className="weather-search-inline-form">
          <input
            type="text"
            className="weather-search-inline-input"
            placeholder="Search place..."
            value={cityInput}
            onChange={(event) => setCityInput(event.target.value)}
            autoFocus
          />
          <button type="submit" className="weather-search-submit-btn" disabled={loading}>
            {loading ? "..." : "Go"}
          </button>
        </form>
      )}

      <div className="weather-top-metric-row">
        <div className="weather-icon-temp-group">
          <div className="weather-main-icon" aria-hidden="true">
            <span className="weather-emoji-glyph">{weather.icon}</span>
          </div>
          <span className="weather-large-temp">{loading ? "--" : weather.temp} deg</span>
        </div>

        <div className="weather-condition-location-group">
          <span className="weather-condition-label">{loading ? "Loading" : weather.condition}</span>
          <span className="weather-location-label">{weather.city}</span>
        </div>
      </div>

      {error && <p className="weather-inline-error">{error}</p>}

      <div className="weather-detail-strip" aria-label="Weather details">
        <span>Feels {weather.feelsLike ?? "--"} deg</span>
        <span>Humidity {weather.humidity ?? "--"}%</span>
        <span>Wind {weather.windSpeed ?? "--"} km/h</span>
      </div>

      <div className="weather-hourly-forecast-strip" role="list" aria-label="Current Conditions">
        {weather.hourly.map((item, idx) => (
          <div key={idx} className="hourly-forecast-column" role="listitem">
            <span className="hourly-time-text">{item.timeLabel}</span>
            <div className="hourly-glyph-box" aria-hidden="true">
              <span className="hourly-emoji">{item.icon}</span>
            </div>
            <span className="hourly-temp-text">{item.temp} deg</span>
          </div>
        ))}
      </div>
    </div>
  );
}
