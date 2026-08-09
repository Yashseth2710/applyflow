// Labels and colours for each stage. Colours are token names, not literals, so
// the board, badges and charts can't drift apart.

import type { ApplicationStatus } from "./types";

export interface StatusMeta {
  label: string;
  /** CSS custom property name, e.g. "--stage-applied". */
  token: string;
  short: string;
}

export const STATUS_META: Record<ApplicationStatus, StatusMeta> = {
  wishlist: { label: "Wishlist", short: "Wishlist", token: "--stage-wishlist" },
  applied: { label: "Applied", short: "Applied", token: "--stage-applied" },
  assessment: {
    label: "Assessment",
    short: "Assessment",
    token: "--stage-assessment",
  },
  phone_screen: {
    label: "Phone screen",
    short: "Phone",
    token: "--stage-phone",
  },
  technical_interview: {
    label: "Technical interview",
    short: "Technical",
    token: "--stage-technical",
  },
  hr_interview: { label: "HR interview", short: "HR", token: "--stage-hr" },
  final_interview: {
    label: "Final interview",
    short: "Final",
    token: "--stage-final",
  },
  offer: { label: "Offer", short: "Offer", token: "--stage-offer" },
  accepted: { label: "Accepted", short: "Accepted", token: "--stage-accepted" },
  rejected: { label: "Rejected", short: "Rejected", token: "--stage-rejected" },
  withdrawn: {
    label: "Withdrawn",
    short: "Withdrawn",
    token: "--stage-withdrawn",
  },
  on_hold: { label: "On hold", short: "On hold", token: "--stage-onhold" },
};

/** Every status, in pipeline order. Used by dropdowns and the detail page. */
export const ALL_STATUSES: ApplicationStatus[] = [
  "wishlist",
  "applied",
  "assessment",
  "phone_screen",
  "technical_interview",
  "hr_interview",
  "final_interview",
  "offer",
  "accepted",
  "rejected",
  "withdrawn",
  "on_hold",
];

// Twelve columns at a readable width is ~3,300px, so interview rounds are
// grouped and terminal states collapse into "Closed". The database still
// stores all twelve — this is presentation only.
export interface BoardColumnDef {
  id: string;
  label: string;
  token: string;
  /** Statuses that land in this column. Dropping targets `primary`. */
  statuses: ApplicationStatus[];
  primary: ApplicationStatus;
}

export const BOARD_COLUMNS: BoardColumnDef[] = [
  {
    id: "wishlist",
    label: "Wishlist",
    token: "--stage-wishlist",
    statuses: ["wishlist"],
    primary: "wishlist",
  },
  {
    id: "applied",
    label: "Applied",
    token: "--stage-applied",
    statuses: ["applied"],
    primary: "applied",
  },
  {
    id: "assessment",
    label: "Assessment",
    token: "--stage-assessment",
    statuses: ["assessment"],
    primary: "assessment",
  },
  {
    id: "interview",
    label: "Interview",
    token: "--stage-technical",
    statuses: ["phone_screen", "technical_interview", "hr_interview"],
    // A card dragged into "Interview" without saying which round lands here;
    // the exact round is set from the card or the detail page.
    primary: "technical_interview",
  },
  {
    id: "final",
    label: "Final",
    token: "--stage-final",
    statuses: ["final_interview"],
    primary: "final_interview",
  },
  {
    id: "offer",
    label: "Offer",
    token: "--stage-offer",
    statuses: ["offer", "accepted"],
    primary: "offer",
  },
];

export const CLOSED_STATUSES: ApplicationStatus[] = [
  "rejected",
  "withdrawn",
  "on_hold",
];

export function columnForStatus(status: ApplicationStatus): string | null {
  const column = BOARD_COLUMNS.find((c) => c.statuses.includes(status));
  return column?.id ?? null;
}

export function isClosed(status: ApplicationStatus): boolean {
  return CLOSED_STATUSES.includes(status);
}

/** Inline style for anything tinted by stage colour. */
export function stageStyle(token: string) {
  return { "--stage": `var(${token})` } as React.CSSProperties;
}
