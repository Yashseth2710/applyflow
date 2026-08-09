"use client";

/** TanStack Query hooks for interviews and reminders. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api-client";
import type {
  Interview,
  InterviewCreate,
  InterviewUpdate,
  InterviewWithApplication,
  ReminderList,
} from "./types";

export const interviewKeys = {
  all: ["interviews"] as const,
  forApplication: (id: string) => ["interviews", "application", id] as const,
  upcoming: () => ["interviews", "upcoming"] as const,
  reminders: () => ["interviews", "reminders"] as const,
};

export function useInterviews(applicationId: string) {
  return useQuery({
    queryKey: interviewKeys.forApplication(applicationId),
    queryFn: () => api.get<Interview[]>(`/interviews?application_id=${applicationId}`),
    enabled: Boolean(applicationId),
  });
}

export function useUpcomingInterviews(limit = 5) {
  return useQuery({
    queryKey: interviewKeys.upcoming(),
    queryFn: () => api.get<InterviewWithApplication[]>(`/interviews/upcoming?limit=${limit}`),
  });
}

export function useReminders() {
  return useQuery({
    queryKey: interviewKeys.reminders(),
    queryFn: () => api.get<ReminderList>("/interviews/reminders"),
  });
}

/** Reminders are derived from applications as well as interviews, so a change
 *  to either can invalidate them. */
function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: interviewKeys.all });
  void qc.invalidateQueries({ queryKey: ["applications"] });
}

export function useCreateInterview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: InterviewCreate) => api.post<Interview>("/interviews", payload),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateInterview(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: InterviewUpdate) => api.patch<Interview>(`/interviews/${id}`, payload),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteInterview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/interviews/${id}`),
    onSuccess: () => invalidateAll(qc),
  });
}
