"use client";

/**
 * One block of the settings page.
 *
 * A real `<section>` with a heading, so the page has an outline a screen
 * reader can jump through rather than one long undifferentiated form.
 */
export function SettingsSection({
  title,
  description,
  children,
  tone = "default",
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  /** "danger" for the irreversible one. */
  tone?: "default" | "danger";
}) {
  const danger = tone === "danger";

  return (
    <section
      aria-labelledby={`${slug(title)}-heading`}
      className={
        danger
          ? "rounded-xl border border-danger/30 bg-danger-subtle/40 p-5 sm:p-6"
          : "rounded-xl border border-border bg-card p-5 sm:p-6"
      }
    >
      <h2
        id={`${slug(title)}-heading`}
        className={`text-base font-semibold ${danger ? "text-danger-ink" : ""}`}
      >
        {title}
      </h2>
      {description && (
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      )}
      <div className="mt-5">{children}</div>
    </section>
  );
}

function slug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}
