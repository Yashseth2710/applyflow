"use client";

/** Analytics query hook, and the formatting the page shares. */

import { useQuery } from "@tanstack/react-query";

import { api } from "./api-client";
import type { AnalyticsSummary } from "./types";

export const analyticsKeys = {
  summary: () => ["analytics", "summary"] as const,
};

export function useAnalytics() {
  return useQuery({
    queryKey: analyticsKeys.summary(),
    queryFn: () => api.get<AnalyticsSummary>("/analytics/summary"),
    // The numbers only move when an application does, and every panel on the
    // page reads this one response.
    staleTime: 60_000,
  });
}

/** A rate as a percentage, or an em dash when the backend withheld it. */
export function formatRate(rate: number | null | undefined): string {
  if (rate === null || rate === undefined) return "—";
  return `${Math.round(rate * 100)}%`;
}

/** Durations read as prose, because "0.4 days" makes nobody wiser. */
export function formatDays(days: number): string {
  if (days < 1) return "under a day";
  const rounded = Math.round(days * 10) / 10;
  return `${rounded} ${rounded === 1 ? "day" : "days"}`;
}
