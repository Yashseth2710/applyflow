import { describe, expect, it } from "vitest";

import {
  ALL_STATUSES,
  BOARD_COLUMNS,
  CLOSED_STATUSES,
  STATUS_META,
  columnForStatus,
  isClosed,
} from "./application-status";
import type { ApplicationStatus } from "./types";

describe("status metadata", () => {
  it("covers every status the API can return", () => {
    // A status with no entry here renders as undefined and crashes the badge,
    // so a new one added to the backend must fail here first.
    for (const status of ALL_STATUSES) {
      expect(STATUS_META[status]).toBeDefined();
      expect(STATUS_META[status].label).not.toBe("");
    }
  });

  it("gives every status its own colour token", () => {
    const tokens = ALL_STATUSES.map((s) => STATUS_META[s].token);
    expect(new Set(tokens).size).toBe(tokens.length);
  });
});

describe("board columns", () => {
  it("places every open status in exactly one column", () => {
    const open = ALL_STATUSES.filter((s) => !CLOSED_STATUSES.includes(s));

    for (const status of open) {
      const columns = BOARD_COLUMNS.filter((c) => c.statuses.includes(status));
      expect(columns).toHaveLength(1);
    }
  });

  it("keeps closed statuses off the board", () => {
    for (const status of CLOSED_STATUSES) {
      expect(columnForStatus(status)).toBeNull();
      expect(isClosed(status)).toBe(true);
    }
  });

  it("drops a card into a status that belongs to the column it landed in", () => {
    // The board writes `primary` when a card is dragged without naming a round.
    for (const column of BOARD_COLUMNS) {
      expect(column.statuses).toContain(column.primary);
    }
  });

  it("groups the interview rounds under one column", () => {
    const interview = BOARD_COLUMNS.find((c) => c.id === "interview");
    expect(interview?.statuses).toEqual(
      expect.arrayContaining<ApplicationStatus>([
        "phone_screen",
        "technical_interview",
        "hr_interview",
      ]),
    );
  });
});
