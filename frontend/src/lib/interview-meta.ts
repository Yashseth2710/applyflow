import type { InterviewMode, InterviewOutcome, InterviewRound } from "./types";

export const ROUND_LABELS: Record<InterviewRound, string> = {
  phone_screen: "Phone screen",
  technical: "Technical",
  take_home: "Take-home",
  system_design: "System design",
  hr: "HR",
  managerial: "Managerial",
  final: "Final round",
  other: "Other",
};

export const ALL_ROUNDS = Object.keys(ROUND_LABELS) as InterviewRound[];

export const MODE_LABELS: Record<InterviewMode, string> = {
  onsite: "On-site",
  video: "Video call",
  phone: "Phone",
};

export const ALL_MODES = Object.keys(MODE_LABELS) as InterviewMode[];

interface OutcomeMeta {
  label: string;
  /** CSS custom property holding the tone colour. */
  token: string;
}

export const OUTCOME_META: Record<InterviewOutcome, OutcomeMeta> = {
  pending: { label: "Scheduled", token: "--stage-applied" },
  passed: { label: "Passed", token: "--success" },
  failed: { label: "Didn't go through", token: "--stage-rejected" },
  cancelled: { label: "Cancelled", token: "--stage-withdrawn" },
};

export const ALL_OUTCOMES = Object.keys(OUTCOME_META) as InterviewOutcome[];

/** Local wall-clock string for a datetime-local input, which has no timezone
 *  and would otherwise shift the value by the UTC offset. */
export function toLocalInputValue(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours(),
  )}:${pad(d.getMinutes())}`;
}

/** The backend rejects a time without an offset, so send a full ISO string
 *  rather than the input's bare local value. */
export function fromLocalInputValue(value: string): string {
  return new Date(value).toISOString();
}
