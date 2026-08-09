"use client";

/** TanStack Query hooks for applications. */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";

import { api } from "./api-client";
import type {
  Application,
  ApplicationCreate,
  ApplicationDetail,
  ApplicationPage,
  ApplicationStatus,
  ApplicationUpdate,
  BoardResponse,
} from "./types";

export interface ListParams {
  status?: ApplicationStatus | "";
  search?: string;
  source?: string;
  sort_by?: "created_at" | "updated_at" | "date_applied" | "company_name" | "job_title";
  order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export const applicationKeys = {
  all: ["applications"] as const,
  list: (params: ListParams) => ["applications", "list", params] as const,
  board: () => ["applications", "board"] as const,
  detail: (id: string) => ["applications", "detail", id] as const,
  sources: () => ["applications", "sources"] as const,
};

function toQueryString(params: ListParams): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    // Skip empties so the URL stays clean and the backend applies its defaults.
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export function useApplications(params: ListParams) {
  return useQuery({
    queryKey: applicationKeys.list(params),
    queryFn: () =>
      api.get<ApplicationPage>(`/applications${toQueryString(params)}`),
    // Keeps the previous page visible while the next one loads, instead of
    // collapsing the table to a spinner on every keystroke or page change.
    placeholderData: (previous) => previous,
  });
}

export function useBoard() {
  return useQuery({
    queryKey: applicationKeys.board(),
    queryFn: () => api.get<BoardResponse>("/applications/board"),
  });
}

export function useApplication(
  id: string,
  options?: Partial<UseQueryOptions<ApplicationDetail>>,
) {
  return useQuery({
    queryKey: applicationKeys.detail(id),
    queryFn: () => api.get<ApplicationDetail>(`/applications/${id}`),
    ...options,
  });
}

export function useSources() {
  return useQuery({
    queryKey: applicationKeys.sources(),
    queryFn: () => api.get<string[]>("/applications/sources"),
    staleTime: 5 * 60_000,
  });
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ApplicationCreate) =>
      api.post<ApplicationDetail>("/applications", payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}

export function useUpdateApplication(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ApplicationUpdate) =>
      api.patch<Application>(`/applications/${id}`, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}

export function useDeleteApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/applications/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}

// Optimistic — the card moves on drop. Waiting for the round trip means it
// hangs for a second or more on a cold database, which reads as a failed drag.
export function useChangeStatus() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      status,
      position,
    }: {
      id: string;
      status: ApplicationStatus;
      position?: number;
    }) =>
      api.patch<Application>(`/applications/${id}/status`, { status, position }),

    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: applicationKeys.board() });
      const previous = qc.getQueryData<BoardResponse>(applicationKeys.board());

      if (previous) {
        const moved = previous.columns
          .flatMap((c) => c.items)
          .find((item) => item.id === id);

        if (moved) {
          const updated: BoardResponse = {
            ...previous,
            columns: previous.columns.map((column) => {
              const withoutMoved = column.items.filter((i) => i.id !== id);
              if (column.status === status) {
                return {
                  ...column,
                  items: [...withoutMoved, { ...moved, status }],
                  count: withoutMoved.length + 1,
                };
              }
              return {
                ...column,
                items: withoutMoved,
                count: withoutMoved.length,
              };
            }),
          };
          qc.setQueryData(applicationKeys.board(), updated);
        }
      }

      return { previous };
    },

    onError: (_err, _vars, context) => {
      if (context?.previous) {
        qc.setQueryData(applicationKeys.board(), context.previous);
      }
    },

    onSettled: () => {
      void qc.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}
