import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("AURA Suite, Nature Browser Chat, & Memory", () => {
  it("tests nature browser chat, dedicated news, and memory page", async () => {
    render(<App />);

    // 1. Verify Top Navigation Bar
    expect(screen.getAllByText("AURA OS").length).toBeGreaterThan(0);
    expect(screen.getByText("Studio & AI")).toBeInTheDocument();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Schedule")).toBeInTheDocument();
    expect(screen.getByText("News")).toBeInTheDocument();
    expect(screen.getByText("Memory")).toBeInTheDocument();
    expect(screen.getByText("Media & Tools")).toBeInTheDocument();

    // 2. Verify Nature Wallpaper Browser Welcome Front
    await waitFor(() => expect(screen.getByText(/Alex,/)).toBeInTheDocument());
    expect(screen.getByText("How can I help you today?")).toBeInTheDocument();

    fireEvent.click(screen.getByTitle("3-Pane Workstation View"));
    await waitFor(() => {
      expect(screen.getByText("How can I help?")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTitle("Focus Mode (Center Canvas Only)"));
    await waitFor(() => expect(screen.getByText(/Alex,/)).toBeInTheDocument());

    // 3. Navigate to Memory Page
    const memoryTab = screen.getByText("Memory");
    fireEvent.click(memoryTab);

    await waitFor(() => {
      expect(screen.getByLabelText("AURA Memory")).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText(/Remember that I prefer/i), { target: { value: "my project pipeline uses MemoryManager before routing" } });
    fireEvent.click(screen.getByText("Save memory"));
    await waitFor(() => {
      expect(screen.getByText("my project pipeline uses MemoryManager before routing")).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText("Find a memory"), { target: { value: "pipeline" } });
    expect(screen.getAllByText("my project pipeline uses MemoryManager before routing").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText("Forget"));
    await waitFor(() => {
      expect(screen.queryAllByText("my project pipeline uses MemoryManager before routing")).toHaveLength(0);
    });

    // 4. Switch to Dedicated News Page
    const newsTab = screen.getByText("News");
    fireEvent.click(newsTab);

    await waitFor(() => {
      expect(screen.getByText("AURA Live News")).toBeInTheDocument();
      expect(screen.getByText("AURA routes local actions without cloud APIs")).toBeInTheDocument();
    });

    // 5. Switch to Executive Dashboard
    const dashboardTab = screen.getByText("Dashboard");
    fireEvent.click(dashboardTab);

    await waitFor(() => {
      expect(screen.getByText("AURA Dashboard")).toBeInTheDocument();
      expect(screen.getByText("Multi View Panel")).toBeInTheDocument();
      expect(screen.getByText("Scheduled Recurring Payments")).toBeInTheDocument();
    });
  });
});
