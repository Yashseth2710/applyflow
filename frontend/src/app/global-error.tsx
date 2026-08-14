"use client";

/**
 * The last resort: a crash in the root layout itself.
 *
 * `error.tsx` renders inside the layout, so it cannot help when the layout is
 * what failed. This one replaces the whole document, which is why it has to
 * carry its own `<html>` and `<body>` — and why it cannot use the app's
 * components or theme tokens, since none of that is mounted at this point.
 *
 * Styles are inline for the same reason. If the stylesheet were the thing that
 * failed to load, a class name here would render as unstyled text on white.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100svh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "0.75rem",
          padding: "1.5rem",
          textAlign: "center",
          background: "#faf9fc",
          color: "#1c1b22",
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
        }}
      >
        <h1 style={{ fontSize: "1.25rem", fontWeight: 600, margin: 0 }}>
          ApplyFlow didn’t start
        </h1>
        <p style={{ margin: 0, maxWidth: "26rem", color: "#56525f" }}>
          Something failed before the page could load. Your data is safe.
        </p>
        <button
          onClick={reset}
          style={{
            marginTop: "0.5rem",
            padding: "0.55rem 1.25rem",
            fontSize: "0.875rem",
            fontWeight: 500,
            color: "#ffffff",
            background: "#6d3fe0",
            border: "none",
            borderRadius: "0.5rem",
            cursor: "pointer",
          }}
        >
          Reload
        </button>
        {error.digest && (
          <p style={{ marginTop: "1.5rem", fontSize: "0.75rem", color: "#56525f" }}>
            Reference: <span style={{ fontFamily: "ui-monospace, monospace" }}>{error.digest}</span>
          </p>
        )}
      </body>
    </html>
  );
}
