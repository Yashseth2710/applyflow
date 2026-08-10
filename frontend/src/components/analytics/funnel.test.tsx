import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { FunnelStep } from "@/lib/types";

import { Funnel } from "./funnel";

function steps(counts: number[], rates: (number | null)[] = []): FunnelStep[] {
  const labels = [
    "Applied",
    "Assessment",
    "Interview",
    "Final round",
    "Offer",
    "Accepted",
  ];
  const keys = [
    "applied",
    "assessment",
    "interview",
    "final",
    "offer",
    "accepted",
  ];
  return counts.map((count, i) => ({
    key: keys[i],
    label: labels[i],
    count,
    rate: rates[i] ?? null,
  }));
}

describe("Funnel", () => {
  it("explains itself instead of drawing six empty bars", () => {
    render(<Funnel steps={steps([0, 0, 0, 0, 0, 0])} />);

    expect(screen.getByText(/nothing sent yet/i)).toBeInTheDocument();
    expect(screen.queryByText("Applied")).not.toBeInTheDocument();
  });

  it("shows counts with a dash where the rate was withheld", () => {
    render(<Funnel steps={steps([4, 2, 1, 0, 0, 0])} />);

    expect(screen.getByText("Applied")).toBeInTheDocument();
    // Counts are honest at any volume; the percentages are what wait.
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it("shows percentages once the backend supplies them", () => {
    render(
      <Funnel
        steps={steps([12, 8, 6, 2, 2, 1], [1, 0.67, 0.5, 0.17, 0.17, 0.08])}
      />,
    );

    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("67%")).toBeInTheDocument();
  });

  it("says how many fell out between one rung and the next", () => {
    render(<Funnel steps={steps([12, 8, 6, 2, 2, 1])} />);

    expect(screen.getByText(/4 didn't get past applied/i)).toBeInTheDocument();
    expect(
      screen.getByText(/2 didn't get past assessment/i),
    ).toBeInTheDocument();
  });

  it("says nothing about drop-off at the top of the funnel", () => {
    render(<Funnel steps={steps([12, 12, 12, 12, 12, 12])} />);

    // Nothing was lost anywhere, so there should be no drop-off lines at all.
    expect(screen.queryByText(/didn't get past/i)).not.toBeInTheDocument();
  });
});
