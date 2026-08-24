import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("AURA Electron renderer", () => {
  it("renders the home experience with real backend status", async () => {
    render(<App />);
    expect(screen.getByText(/AURA is local-first/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Backend: READY/)).toBeInTheDocument());
    expect(screen.getByText("AURA Status")).toBeInTheDocument();
    expect(screen.getByText(/Task storage/)).toBeInTheDocument();
  });
});
