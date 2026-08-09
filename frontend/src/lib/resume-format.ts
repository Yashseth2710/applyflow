import type { ExtractionStatus } from "./types";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${Math.round(kb)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

interface ExtractionMeta {
  label: string;
  /** CSS custom property holding the tone colour. */
  tone: string;
  /** Whether this state needs the user to do something. */
  actionable: boolean;
}

export const EXTRACTION_META: Record<ExtractionStatus, ExtractionMeta> = {
  ok: { label: "Text ready", tone: "--success", actionable: false },
  empty: { label: "No text found", tone: "--warning", actionable: true },
  failed: { label: "Unreadable", tone: "--danger", actionable: true },
  pending: { label: "Processing", tone: "--muted-foreground", actionable: false },
};
