import { describe, expect, it } from "vitest";

import { EXTRACTION_META, formatBytes } from "./resume-format";
import type { ExtractionStatus } from "./types";

describe("formatBytes", () => {
  it("uses the unit that keeps the number readable", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatBytes(1024 * 1024 * 2.5)).toBe("2.5 MB");
  });

  it("switches unit exactly at the boundary", () => {
    expect(formatBytes(1023)).toBe("1023 B");
    expect(formatBytes(1024)).toBe("1 KB");
    expect(formatBytes(1024 * 1024)).toBe("1.0 MB");
  });

  it("handles an empty file", () => {
    expect(formatBytes(0)).toBe("0 B");
  });
});

describe("extraction status metadata", () => {
  const statuses: ExtractionStatus[] = ["ok", "empty", "failed", "pending"];

  it("covers every extraction status", () => {
    for (const status of statuses) {
      expect(EXTRACTION_META[status]).toBeDefined();
    }
  });

  it("only asks the user to act when they actually can", () => {
    // Pending resolves on its own and ok is fine; telling someone to fix
    // either one sends them looking for a problem that isn't there.
    expect(EXTRACTION_META.ok.actionable).toBe(false);
    expect(EXTRACTION_META.pending.actionable).toBe(false);
    expect(EXTRACTION_META.empty.actionable).toBe(true);
    expect(EXTRACTION_META.failed.actionable).toBe(true);
  });
});
