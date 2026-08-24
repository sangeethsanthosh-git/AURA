import { describe, expect, it } from "vitest";
import { widgetRegistry } from "./widgets";

describe("widget registry", () => {
  it("defines modular widgets with unique ids and data sources", () => {
    const ids = widgetRegistry.map((widget) => widget.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(widgetRegistry.every((widget) => widget.dataSource && widget.refreshPolicy)).toBe(true);
  });
});
