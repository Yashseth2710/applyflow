import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { VolumePoint } from "@/lib/types";

import { Activity } from "./activity";

function weeks(points: [string, number, number][]): VolumePoint[] {
  return points.map(([week_start, created, moved]) => ({
    week_start,
    created,
    moved,
  }));
}

describe("Activity", () => {
  it("describes the chart for anyone who cannot see it", () => {
    render(
      <Activity
        volume={weeks([
          ["2026-07-20", 2, 1],
          ["2026-07-27", 5, 3],
          ["2026-08-03", 1, 4],
        ])}
      />,
    );

    // An SVG on its own reads as nothing at all.
    const chart = screen.getByRole("img");
    expect(chart).toHaveAccessibleName(/8 applications added/);
    expect(chart).toHaveAccessibleName(/8 stage changes/);
    expect(chart).toHaveAccessibleName(/busiest in the week of 27 Jul/);
  });

  it("says so plainly when the window is empty", () => {
    render(
      <Activity
        volume={weeks([
          ["2026-07-27", 0, 0],
          ["2026-08-03", 0, 0],
        ])}
      />,
    );

    expect(
      screen.getByText(/nothing recorded in this window yet/i),
    ).toBeInTheDocument();
    // No chart to describe, so no image role either.
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
