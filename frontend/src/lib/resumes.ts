"use client";

/** TanStack Query hooks for resumes. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api-client";
import type {
  Resume,
  ResumeDetail,
  ResumeText,
  ResumeUpdate,
  ResumeUpload,
  ResumeUsage,
} from "./types";

export const resumeKeys = {
  all: ["resumes"] as const,
  list: () => ["resumes", "list"] as const,
  detail: (id: string) => ["resumes", "detail", id] as const,
  text: (id: string) => ["resumes", "text", id] as const,
  usage: (id: string) => ["resumes", "usage", id] as const,
};

export interface UploadArgs {
  file: File;
  title?: string;
  notes?: string;
  /** Set to add a version to an existing resume rather than create a new one. */
  replacesId?: string;
}

export function useResumes() {
  return useQuery({
    queryKey: resumeKeys.list(),
    queryFn: () => api.get<Resume[]>("/resumes"),
  });
}

export function useResume(id: string) {
  return useQuery({
    queryKey: resumeKeys.detail(id),
    queryFn: () => api.get<ResumeDetail>(`/resumes/${id}`),
    enabled: Boolean(id),
  });
}

export function useResumeText(id: string, enabled = true) {
  return useQuery({
    queryKey: resumeKeys.text(id),
    queryFn: () => api.get<ResumeText>(`/resumes/${id}/text`),
    enabled: Boolean(id) && enabled,
    // The text only changes when a new version is uploaded, which invalidates
    // this key anyway.
    staleTime: 5 * 60_000,
  });
}

export function useResumeUsage(id: string, enabled = true) {
  return useQuery({
    queryKey: resumeKeys.usage(id),
    queryFn: () => api.get<ResumeUsage>(`/resumes/${id}/usage`),
    enabled: Boolean(id) && enabled,
  });
}

export function useUploadResume() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({ file, title, notes, replacesId }: UploadArgs) => {
      const form = new FormData();
      form.append("file", file);
      if (title) form.append("title", title);
      if (notes) form.append("notes", notes);
      if (replacesId) form.append("replaces_id", replacesId);
      return api.upload<ResumeUpload>("/resumes", form);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: resumeKeys.all });
    },
  });
}

export function useUpdateResume(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ResumeUpdate) => api.patch<Resume>(`/resumes/${id}`, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: resumeKeys.all });
    },
  });
}

export function useSetCurrentVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Resume>(`/resumes/${id}/set-current`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: resumeKeys.all });
    },
  });
}

export function useDeleteResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/resumes/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: resumeKeys.all });
      // An application's resume_id becomes null when its resume goes.
      void qc.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

/**
 * Fetch the file and hand it to the browser.
 *
 * Not a plain link: the access token lives in memory and goes out as a header,
 * and the refresh cookie is scoped to the auth routes, so an <a href> to the
 * download endpoint arrives unauthenticated and 401s.
 */
export async function openResumeFile(id: string, filename: string, download = false) {
  const response = await api.raw(`/resumes/${id}/download`);
  const url = URL.createObjectURL(await response.blob());

  try {
    if (download) {
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
    } else {
      window.open(url, "_blank", "noopener");
    }
  } finally {
    // Long enough for the tab to load or the download to start. Revoking
    // immediately cancels both.
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  }
}
