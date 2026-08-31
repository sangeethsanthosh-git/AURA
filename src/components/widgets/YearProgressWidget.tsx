import { useMemo, useState } from "react";

interface YearProgressWidgetProps {
  initialTheme?: "light" | "dark";
  customPercentage?: number;
}

export function YearProgressWidget({
  initialTheme = "light",
  customPercentage,
}: YearProgressWidgetProps) {
  const [theme, setTheme] = useState<"light" | "dark">(initialTheme);

  // Calculate real year progress
  const percentage = useMemo(() => {
    if (customPercentage !== undefined) return customPercentage;
    const now = new Date();
    const startOfYear = new Date(now.getFullYear(), 0, 1);
    const endOfYear = new Date(now.getFullYear() + 1, 0, 1);
    const progress = (now.getTime() - startOfYear.getTime()) / (endOfYear.getTime() - startOfYear.getTime());
    return Math.round(progress * 100);
  }, [customPercentage]);

  // 4 rows x 12 columns = 48 dots
  const totalDots = 48;
  const filledDotsCount = Math.round((percentage / 100) * totalDots);

  return (
    <div
      className={`minimal-year-card minimal-year-card--${theme}`}
      aria-label="Year Progress Matrix Widget"
    >
      {/* Top Header Row */}
      <div className="year-card-header">
        <h3 className="year-main-title">Year</h3>
        <div className="year-header-right">
          <span className="year-percent-text">{percentage}%</span>
          <button
            type="button"
            className="year-theme-toggle-btn"
            onClick={() => setTheme((prev) => (prev === "light" ? "dark" : "light"))}
            title={`Switch to ${theme === "light" ? "Dark" : "Light"} mode`}
          >
            {theme === "light" ? "🌙" : "☀️"}
          </button>
        </div>
      </div>

      {/* 4 x 12 Dot Matrix Grid (Matching Reference Image) */}
      <div className="year-dot-matrix-grid" role="grid" aria-label="Year progress dot matrix">
        {Array.from({ length: totalDots }).map((_, idx) => {
          const isFilled = idx < filledDotsCount;
          return (
            <span
              key={idx}
              className={`matrix-dot ${isFilled ? "matrix-dot--filled" : "matrix-dot--empty"}`}
            />
          );
        })}
      </div>
    </div>
  );
}

