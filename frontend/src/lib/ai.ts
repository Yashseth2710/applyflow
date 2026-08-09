"use client";

/** TanStack Query hooks for the AI features. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api-client";
import type { AIOutput, AIOutputList, AIStatus, AITask } from "./types";

export const aiKeys = {
  all: ["ai"] as const,
  status: () => ["ai", "status"] as const,
  forApplication: (id: string) => ["ai", "application", id] as const,
};

export function useAIStatus() {
  return useQuery({
    queryKey: aiKeys.status(),
    queryFn: () => api.get<AIStatus>("/ai/status"),
    // Changes only when the server is reconfigured.
    staleTime: 10 * 60_000,
  });
}

export function useAIOutputs(applicationId: string) {
  return useQuery({
    queryKey: aiKeys.forApplication(applicationId),
    queryFn: () => api.get<AIOutputList>(`/ai/applications/${applicationId}`),
    enabled: Boolean(applicationId),
  });
}

export function useGenerate(applicationId: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({ task, force = false }: { task: AITask; force?: boolean }) =>
      api.post<AIOutput>(
        `/ai/applications/${applicationId}/${task}?force=${force}`,
        undefined,
        // Generous: a first generation runs the model, and a reasoning model
        // spends time thinking before it writes anything.
        { timeoutMs: 120_000 },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: aiKeys.forApplication(applicationId) });
    },
  });
}
