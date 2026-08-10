"use client";

import { Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { initials, useClearAvatar, useSetAvatar } from "@/lib/account";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

const MAX_MB = 5;
const ACCEPTED = "image/jpeg,image/png,image/webp,image/gif";

export function AvatarField() {
  const { user, applyUser } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const setAvatar = useSetAvatar();
  const clearAvatar = useClearAvatar();
  const [error, setError] = useState<string | null>(null);

  const busy = setAvatar.isPending || clearAvatar.isPending;

  function choose(file: File | undefined) {
    if (!file) return;
    setError(null);

    // Checked here as well as on the server, so an obvious mistake does not
    // cost a multi-megabyte round trip.
    if (!ACCEPTED.split(",").includes(file.type)) {
      setError("Choose a JPEG, PNG, WebP or GIF image.");
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`That image is larger than the ${MAX_MB} MB limit.`);
      return;
    }

    setAvatar.mutate(file, {
      onSuccess: (updated) => {
        applyUser(updated);
        toast.success("Picture updated");
      },
      onError: (err) =>
        setError(
          err instanceof ApiError ? err.message : "That image could not be uploaded.",
        ),
    });
  }

  return (
    <div className="flex flex-wrap items-center gap-5">
      {user?.avatar ? (
        // A data URI has nothing for next/image to optimise — the bytes are
        // already inline, already 256px, and already WebP.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={user.avatar}
          alt=""
          width={80}
          height={80}
          className="size-20 shrink-0 rounded-full object-cover ring-1 ring-border"
        />
      ) : (
        // aria-hidden: the initials are decoration here. The person's name is
        // already in the field below, and hearing it twice helps nobody.
        <span
          aria-hidden
          className="flex size-20 shrink-0 items-center justify-center rounded-full bg-accent text-xl font-semibold text-accent-foreground"
        >
          {initials(user)}
        </span>
      )}

      <div className="min-w-0">
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            className="h-9"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
          >
            <Upload aria-hidden />
            {user?.avatar ? "Change picture" : "Upload a picture"}
          </Button>

          {user?.avatar && (
            <Button
              type="button"
              variant="ghost"
              className="h-9"
              disabled={busy}
              onClick={() =>
                clearAvatar.mutate(undefined, {
                  onSuccess: (updated) => {
                    applyUser(updated);
                    toast.success("Picture removed");
                  },
                })
              }
            >
              <Trash2 aria-hidden />
              Remove
            </Button>
          )}
        </div>

        <p className="mt-2 text-xs text-muted-foreground">
          JPEG, PNG, WebP or GIF, up to {MAX_MB} MB. Cropped to a square and
          resized — the original is not kept.
        </p>

        {error && (
          <p role="alert" className="mt-1.5 text-sm text-danger">
            {error}
          </p>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="sr-only"
        // Out of the accessibility tree and out of the tab order. A file input
        // is announced as a button, so left exposed it is a second, unlabelled
        // "Profile picture" control sitting next to the real one — the button
        // above is what opens it, for mouse and keyboard alike.
        aria-hidden
        tabIndex={-1}
        disabled={busy}
        onChange={(e) => {
          choose(e.target.files?.[0]);
          // Reset, or picking the same file twice in a row fires nothing.
          e.target.value = "";
        }}
      />
    </div>
  );
}
