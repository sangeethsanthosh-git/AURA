import { ReactNode } from "react";

export function WidgetCard({ title, size, children }: { title: string; size: string; children: ReactNode }) {
  return (
    <section className="widget-card" data-size={size}>
      <header>
        <h2>{title}</h2>
      </header>
      {children}
    </section>
  );
}
