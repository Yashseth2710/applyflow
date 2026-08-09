"use client";

import { Upload } from "lucide-react";
import { useRef, useState } from "react";

import { cn } from "@/lib/utils";

const MAX_MB = 5;

/**
 * Drag-and-drop plus a real file input.
 *
 * The input stays in the DOM rather than being created on click: it is what
 * makes the control reachable by keyboard, and the drop zone is a label for it.
 */
export function UploadDropzone({
  onFile,
  disabled,
  label = "Drop a PDF here, or click to choose one",
  compact = false,
  className,
}: {
  onFile: (file: File) => void;
  disabled?: boolean;
  label?: string;
  /** Slimmer version, for when the zone is no longer the point of the page. */
  compact?: boolean;
  className?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  function accept(file: File | undefined) {
    if (!file) return;
    setLocalError(null);

    // Checked here as well as on the server, so an obvious mistake doesn't cost
    // a multi-megabyte round trip.
    if (file.type !== "application/pdf") {
      setLocalError("Only PDF files are accepted.");
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setLocalError(`That file is larger than the ${MAX_MB} MB limit.`);
      return;
    }
    onFile(file);
  }

  return (
    <div className={className}>
      <label
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!disabled) accept(e.dataTransfer.files[0]);
        }}
        className={cn(
          "flex cursor-pointer rounded-xl border-2 border-dashed transition-colors",
          compact
            ? "items-center gap-3 px-4 py-3"
            : "flex-col items-center justify-center px-6 py-10 text-center",
          dragging
            ? "border-primary bg-accent"
            : "border-border bg-surface hover:border-primary/40 hover:bg-accent/40",
          disabled && "pointer-events-none opacity-60",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="sr-only"
          disabled={disabled}
          onChange={(e) => {
            accept(e.target.files?.[0]);
            // Reset, or picking the same file twice in a row fires nothing.
            e.target.value = "";
          }}
        />

        <span
          className={cn(
            "inline-flex items-center justify-center rounded-xl",
            compact ? "size-9 shrink-0" : "mb-3 size-11",
          )}
          style={{ background: "var(--accent)", color: "var(--primary)" }}
        >
          <Upload className={compact ? "size-4" : "size-5"} aria-hidden />
        </span>

        {compact ? (
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium">{label}</span>
            <span className="block text-xs text-muted-foreground">
              PDF only, up to {MAX_MB} MB
            </span>
          </span>
        ) : (
          <>
            <span className="text-sm font-medium">{label}</span>
            <span className="mt-1 text-xs text-muted-foreground">
              PDF only, up to {MAX_MB} MB
            </span>
          </>
        )}
      </label>

      {localError && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {localError}
        </p>
      )}
    </div>
  );
}
