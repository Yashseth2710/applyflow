"use client";

import { format, parseISO } from "date-fns";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { VolumePoint } from "@/lib/types";

interface Point extends VolumePoint {
  label: string;
}

export function Activity({ volume }: { volume: VolumePoint[] }) {
  const data: Point[] = volume.map((point) => ({
    ...point,
    label: format(parseISO(point.week_start), "d MMM"),
  }));

  const busiest = Math.max(...data.map((d) => Math.max(d.created, d.moved)), 0);

  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-muted-foreground">
            Activity
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            The last twelve weeks, by week.
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <Key token="--chart-1" label="Added" />
          <Key token="--chart-4" label="Moved a stage" />
        </div>
      </div>

      {busiest === 0 ? (
        <p className="mt-8 mb-6 text-center text-sm text-muted-foreground">
          Nothing recorded in this window yet.
        </p>
      ) : (
        <div className="mt-5 h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              margin={{ top: 4, right: 4, bottom: 0, left: -20 }}
            >
              <CartesianGrid
                vertical={false}
                stroke="var(--border)"
                strokeDasharray="3 3"
              />
              <XAxis
                dataKey="label"
                tickLine={false}
                axisLine={false}
                tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                // Twelve labels don't fit on a phone; recharts drops the ones
                // that would collide rather than overlapping them.
                interval="preserveStartEnd"
                minTickGap={12}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
                width={40}
                tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              />
              <Tooltip
                cursor={{ fill: "var(--muted)", opacity: 0.5 }}
                content={<WeekTooltip />}
              />
              {/* The grow-in animation replays on every resize, so dragging a
                  window edge collapses the chart to nothing and rebuilds it. */}
              <Bar
                dataKey="created"
                fill="var(--chart-1)"
                radius={[3, 3, 0, 0]}
                isAnimationActive={false}
              />
              <Bar
                dataKey="moved"
                fill="var(--chart-4)"
                radius={[3, 3, 0, 0]}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

function Key({ token, label }: { token: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-muted-foreground">
      <span
        className="size-2.5 rounded-sm"
        style={{ backgroundColor: `var(${token})` }}
        aria-hidden
      />
      {label}
    </span>
  );
}

function WeekTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: Point }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;

  return (
    <div className="rounded-lg border border-border bg-surface-raised px-3 py-2 text-xs shadow-sm">
      <p className="font-medium">Week of {point.label}</p>
      <p className="mt-1 text-muted-foreground">
        {point.created} added · {point.moved} moved
      </p>
    </div>
  );
}
