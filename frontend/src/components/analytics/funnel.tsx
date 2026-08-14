"use client";

import { formatRate } from "@/lib/analytics";
import type { FunnelStep } from "@/lib/types";

/** Token per rung, borrowed from the board so the two agree on what an
 *  "interview" looks like. The keys are funnel groups, not statuses — the
 *  three interview rounds collapse into one bar. */
const STEP_TOKEN: Record<string, string> = {
  applied: "--stage-applied",
  assessment: "--stage-assessment",
  interview: "--stage-technical",
  final: "--stage-final",
  offer: "--stage-offer",
  accepted: "--stage-accepted",
};

export function Funnel({ steps }: { steps: FunnelStep[] }) {
  const sent = steps[0]?.count ?? 0;
  // Scaled against the top of the funnel rather than the largest bar, so the
  // shape stays a funnel instead of always filling the width.
  const top = Math.max(1, sent);

  return (
    <section className="rounded-xl border border-border bg-card p-5 sm:p-6">
      <h2 className="eyebrow">Funnel</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        How far applications got, counting every stage they passed through — not
        only where they sit now.
      </p>

      {sent === 0 ? (
        // Six empty bars are honest and useless. Say why instead.
        <p className="mt-6 text-sm text-muted-foreground">
          Nothing sent yet. Once an application moves out of the wishlist, its
          journey shows up here.
        </p>
      ) : (
        <ol className="mt-5 space-y-3">
          {steps.map((step, index) => {
            const previous = steps[index - 1];
            // Drop-off is only meaningful against the rung above, and only once
            // there was something there to drop off from.
            const lost = previous ? previous.count - step.count : 0;

            return (
              <li key={step.key}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="font-medium">{step.label}</span>
                  <span className="flex items-baseline gap-2">
                    <span className="tabular font-semibold">{step.count}</span>
                    <span className="tabular w-9 text-right text-xs text-muted-foreground">
                      {formatRate(step.rate)}
                    </span>
                  </span>
                </div>

                {/* The count and rate above already say this; the bar is a
                    picture of the same number. */}
                <div
                  className="mt-1.5 h-2.5 overflow-hidden rounded-full bg-muted"
                  aria-hidden
                >
                  <div
                    className="h-full rounded-full transition-[width] duration-500"
                    style={{
                      width: `${(step.count / top) * 100}%`,
                      backgroundColor: `var(${STEP_TOKEN[step.key]})`,
                    }}
                  />
                </div>

                {lost > 0 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {lost} didn’t get past {previous?.label.toLowerCase()}
                  </p>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
