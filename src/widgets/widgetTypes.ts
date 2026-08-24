import { ReactNode } from "react";

export type WidgetSize = "small" | "medium" | "large" | "wide" | "full";

export interface WidgetDefinition {
  id: string;
  title: string;
  size: WidgetSize;
  priority: number;
  refreshPolicy: "manual" | "on-load" | "event";
  dataSource: string;
  render: () => ReactNode;
}
