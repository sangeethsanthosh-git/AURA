import { widgetRegistry } from "./widgets";
import { WidgetCard } from "./WidgetCard";

export function WidgetGrid() {
  return (
    <div className="widget-grid">
      {widgetRegistry
        .slice()
        .sort((a, b) => a.priority - b.priority)
        .map((widget) => (
          <WidgetCard key={widget.id} title={widget.title} size={widget.size}>
            {widget.render()}
          </WidgetCard>
        ))}
    </div>
  );
}
