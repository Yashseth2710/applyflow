"use client";

/** Mutations for the settings page. */

import { useMutation } from "@tanstack/react-query";

import { api } from "./api-client";
import type { AccountDelete, PasswordChange, ProfileUpdate, User } from "./types";

/** Timezones the browser knows about, for the preferences picker.
 *
 * `supportedValuesOf` is the whole IANA list — several hundred entries, which
 * is a lot to scroll but is the only correct answer. A curated shortlist would
 * be wrong for anyone the author did not think of. */
export function timezones(): string[] {
  try {
    return Intl.supportedValuesOf("timeZone");
  } catch {
    // Older engines have neither the method nor a usable substitute. Falling
    // back to whatever the browser is set to keeps the field working.
    return [detectedTimezone()].filter(Boolean) as string[];
  }
}

export function detectedTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return "";
  }
}

/** Two letters from the name, for when there is no picture. */
export function initials(user: Pick<User, "first_name" | "last_name"> | null): string {
  if (!user) return "?";
  const letters = `${user.first_name?.[0] ?? ""}${user.last_name?.[0] ?? ""}`;
  return letters.toUpperCase() || "?";
}

export function useUpdateProfile() {
  return useMutation({
    mutationFn: (payload: ProfileUpdate) => api.patch<User>("/users/me", payload),
  });
}

export function useSetAvatar() {
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      // PUT rather than POST: there is one picture per account, and sending
      // another replaces it rather than adding to a collection.
      return api.upload<User>("/users/me/avatar", form, { method: "PUT" });
    },
  });
}

export function useClearAvatar() {
  return useMutation({
    mutationFn: () => api.delete<User>("/users/me/avatar"),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (payload: PasswordChange) =>
      api.post<void>("/users/me/password", payload),
  });
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: (payload: AccountDelete) => api.delete<void>("/users/me", payload),
  });
}
