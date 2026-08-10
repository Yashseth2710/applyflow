import { describe, expect, it } from "vitest";

import { formatDays, formatRate } from "./analytics";

describe("formatRate", () => {
  it("shows a rate as a whole percentage", () => {
    expect(formatRate(0.6)).toBe("60%");
    expect(formatRate(1)).toBe("100%");
    expect(formatRate(0)).toBe("0%");
  });

  it("shows a dash when the backend withheld the rate", () => {
    // null is the backend saying "not enough data to answer", which is not the
    // same as zero and must never render as 0%.
    expect(formatRate(null)).toBe("—");
    expect(formatRate(undefined)).toBe("—");
  });

  it("rounds rather than truncating", () => {
    expect(formatRate(0.336)).toBe("34%");
  });
});

describe("formatDays", () => {
  it("avoids fake precision below a day", () => {
    // "0.4 days" makes nobody wiser, and a stage that took two hours reading
    // as "0 days" looks like a bug.
    expect(formatDays(0)).toBe("under a day");
    expect(formatDays(0.4)).toBe("under a day");
    expect(formatDays(0.99)).toBe("under a day");
  });

  it("keeps one decimal place above a day", () => {
    expect(formatDays(7.94)).toBe("7.9 days");
    expect(formatDays(11)).toBe("11 days");
  });

  it("uses the singular for exactly one day", () => {
    expect(formatDays(1)).toBe("1 day");
  });
});
