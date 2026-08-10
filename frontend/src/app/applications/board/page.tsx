"use client";

import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { Link } from "@/components/ui/link";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { StatusBadge } from "@/components/applications/status-badge";
import { AppShell } from "@/components/layout/app-shell";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BOARD_COLUMNS,
  CLOSED_STATUSES,
  STATUS_META,
  type BoardColumnDef,
} from "@/lib/application-status";
import { useBoard, useChangeStatus } from "@/lib/applications";
import type { Application, ApplicationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function BoardPage() {
  return (
    <AppShell>
      <Board />
    </AppShell>
  );
}

function Board() {
  const { data, isPending, isError, error } = useBoard();
  const changeStatus = useChangeStatus();
  const [dragging, setDragging] = useState<Application | null>(null);
  const [showClosed, setShowClosed] = useState(false);

  // A pointer must travel 6px before a drag starts, otherwise a plain click on
  // a card gets swallowed and the link never fires.
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  );

  const byStatus = useMemo(() => {
    const map = new Map<ApplicationStatus, Application[]>();
    for (const column of data?.columns ?? []) {
      map.set(column.status as ApplicationStatus, column.items);
    }
    return map;
  }, [data]);

  const closed = useMemo(
    () => CLOSED_STATUSES.flatMap((s) => byStatus.get(s) ?? []),
    [byStatus],
  );

  function itemsFor(column: BoardColumnDef): Application[] {
    return column.statuses.flatMap((s) => byStatus.get(s) ?? []);
  }

  function handleDragStart(event: DragStartEvent) {
    setDragging((event.active.data.current?.application as Application) ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    setDragging(null);
    const { active, over } = event;
    if (!over) return;

    const application = active.data.current?.application as Application | undefined;
    const targetStatus = over.data.current?.status as ApplicationStatus | undefined;
    if (!application || !targetStatus) return;

    // Dropping into the column a card already lives in is a no-op. The backend
    // ignores it too, but skipping the request avoids a pointless round trip.
    if (application.status === targetStatus) return;

    changeStatus.mutate(
      { id: application.id, status: targetStatus },
      {
        onError: () =>
          toast.error("Couldn't move that application", {
            description: "Put it back where it was. Check your connection and retry.",
          }),
      },
    );
  }

  if (isError) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="rounded-xl border border-danger/25 bg-danger-subtle p-6 text-sm">
          <p className="font-medium text-danger">Couldn&apos;t load the board</p>
          <p className="mt-1 text-danger/80">
            {error instanceof Error ? error.message : "Unknown error"}
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-[1600px] px-6 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Pipeline</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {isPending
              ? "Loading…"
              : "Drag a card to move it between stages."}
          </p>
        </div>
        <Link
          href="/applications/new"
          className={cn(buttonVariants(), "h-10 px-4")}
        >
          Add application
        </Link>
      </div>

      {isPending ? (
        <div className="mt-6 grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          {BOARD_COLUMNS.map((c) => (
            <Skeleton key={c.id} className="h-64 rounded-xl" />
          ))}
        </div>
      ) : (
        <DndContext
          sensors={sensors}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="mt-6 grid gap-4 md:grid-cols-3 xl:grid-cols-6">
            {BOARD_COLUMNS.map((column) => (
              <Column
                key={column.id}
                column={column}
                applications={itemsFor(column)}
              />
            ))}
          </div>

          {/* Rendered outside the columns so the dragged card follows the
              cursor without being clipped by a column's overflow. */}
          <DragOverlay>
            {dragging ? <Card application={dragging} overlay /> : null}
          </DragOverlay>
        </DndContext>
      )}

      {!isPending && closed.length > 0 && (
        <section className="mt-8">
          <button
            onClick={() => setShowClosed((v) => !v)}
            className="flex w-full items-center gap-2 rounded-lg border border-border bg-surface px-4 py-3 text-left text-sm font-medium transition-colors hover:bg-muted"
            aria-expanded={showClosed}
          >
            <svg
              className={cn(
                "size-4 transition-transform",
                showClosed && "rotate-90",
              )}
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <path d="m6 4 4 4-4 4" />
            </svg>
            Closed
            <span className="text-muted-foreground">({closed.length})</span>
            <span className="ml-auto flex gap-3 text-xs font-normal text-muted-foreground">
              {CLOSED_STATUSES.map((s) => {
                const count = byStatus.get(s)?.length ?? 0;
                return count > 0 ? (
                  <span key={s}>
                    {STATUS_META[s].label} {count}
                  </span>
                ) : null;
              })}
            </span>
          </button>

          {showClosed && (
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {closed.map((application) => (
                <Card key={application.id} application={application} static />
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  );
}

function Column({
  column,
  applications,
}: {
  column: BoardColumnDef;
  applications: Application[];
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
    data: { status: column.primary },
  });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex min-h-64 flex-col rounded-xl border bg-surface/60 p-3 transition-colors",
        isOver ? "border-primary bg-accent/50" : "border-border",
      )}
    >
      <div className="mb-3 flex items-center gap-2 px-1">
        <span
          className="size-2 rounded-full"
          style={{ backgroundColor: `var(${column.token})` }}
        />
        <span className="text-sm font-medium">{column.label}</span>
        <span className="tabular ml-auto text-xs text-muted-foreground">
          {applications.length}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-2">
        {applications.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border px-3 py-6 text-center text-xs text-muted-foreground">
            Drop here
          </p>
        ) : (
          applications.map((application) => (
            <DraggableCard key={application.id} application={application} />
          ))
        )}
      </div>
    </div>
  );
}

function DraggableCard({ application }: { application: Application }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: application.id,
    data: { application },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      // The original stays in place but fades, so the column doesn't reflow
      // under the cursor mid-drag.
      className={cn("touch-none", isDragging && "opacity-40")}
    >
      <Card application={application} />
    </div>
  );
}

function Card({
  application,
  overlay = false,
  static: isStatic = false,
}: {
  application: Application;
  overlay?: boolean;
  static?: boolean;
}) {
  const body = (
    <>
      <p className="truncate text-sm font-medium">{application.job_title}</p>
      <p className="mt-0.5 truncate text-xs text-muted-foreground">
        {application.company_name}
      </p>
      <div className="mt-2 flex items-center gap-2">
        <StatusBadge status={application.status} short />
        {application.location && (
          <span className="truncate text-xs text-muted-foreground">
            {application.location}
          </span>
        )}
      </div>
    </>
  );

  const className = cn(
    "rounded-lg border border-border bg-card p-3",
    overlay && "cursor-grabbing shadow-lg ring-1 ring-primary/30",
    !overlay && !isStatic && "cursor-grab hover:border-primary/40",
  );

  if (isStatic) {
    return (
      <Link href={`/applications/${application.id}`} className={cn(className, "block hover:border-primary/40")}>
        {body}
      </Link>
    );
  }

  return <div className={className}>{body}</div>;
}
