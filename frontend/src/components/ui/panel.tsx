import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

/*
  Every region in the app was written as `rounded-xl border border-border
  bg-card p-5`, copied by hand into a dozen files. That is not a system, it is
  the same guess made a dozen times, and it is why a chart, a reminders list
  and a delete confirmation all arrived at the same visual volume — the reader
  had no way to tell which one mattered.

  An edge or an elevation, never both. A hairline border together with a
  diffuse shadow on the same element is one of the most recognisable
  generated-UI signatures: it is two different ways of saying "this is a
  separate thing", applied at once because neither was actually chosen. A
  shadow also claims the element is physically lifted off the page, and a
  panel that just sits there is not.

  So:

    flat     the default, and what almost every region should be. A hairline
             says "separate thing" quietly and completely.
    raised   genuinely lifted, and nothing else: a dialog, a menu, something
             mid-drag, the product still on the marketing page. Shadow, no
             border — the shadow is already doing that job.
    sunken   inert or awaiting something — empty states, read-only extracts,
             the ground beneath a list.

  Nested panels are banned outright, which is why `flat` exists: the inner
  thing gets a heading and spacing instead of a second border.
*/
const panelVariants = cva("rounded-xl", {
  variants: {
    level: {
      flat: "border border-border bg-card",
      raised: "bg-surface-raised shadow-[var(--shadow-float)]",
      sunken: "border border-border/70 bg-surface",
    },
    pad: {
      none: "",
      sm: "p-4",
      md: "p-5 sm:p-6",
      lg: "p-6 sm:p-8",
    },
  },
  defaultVariants: { level: "flat", pad: "md" },
});

export function Panel({
  className,
  level,
  pad,
  ...props
}: React.ComponentProps<"section"> & VariantProps<typeof panelVariants>) {
  return <section className={cn(panelVariants({ level, pad }), className)} {...props} />;
}

/**
 * A panel's title row: the label on the left, an optional action on the right.
 *
 * The title is the `eyebrow` size — small, uppercase, muted. These labels name
 * a region, they are not competing for the page's attention, and sizing them
 * near the page title (which is what the old `text-sm font-medium` did next to
 * a `text-2xl` h1) flattened the hierarchy on every screen.
 */
export function PanelHeader({
  title,
  action,
  className,
}: {
  title: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-between gap-3", className)}>
      <h2 className="eyebrow">{title}</h2>
      {action}
    </div>
  );
}

export { panelVariants };
