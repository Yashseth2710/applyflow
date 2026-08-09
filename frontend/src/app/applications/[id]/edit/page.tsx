"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { ApplicationForm } from "@/components/applications/application-form";
import { AppShell } from "@/components/layout/app-shell";
import { Skeleton } from "@/components/ui/skeleton";
import { useApplication, useUpdateApplication } from "@/lib/applications";
import type { ApplicationUpdate } from "@/lib/types";

export default function EditApplicationPage() {
  return (
    <AppShell>
      <EditApplication />
    </AppShell>
  );
}

function EditApplication() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data, isPending, isError } = useApplication(id);
  const update = useUpdateApplication(id);

  if (isPending) {
    return (
      <main className="mx-auto max-w-3xl space-y-4 px-6 py-8">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-96 w-full rounded-xl" />
      </main>
    );
  }

  if (isError || !data) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-8">
        <p className="text-sm text-muted-foreground">
          That application doesn&apos;t exist.{" "}
          <Link href="/applications" className="text-primary hover:underline">
            Back to applications
          </Link>
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <Link
        href={`/applications/${id}`}
        className="text-sm text-muted-foreground hover:text-foreground"
      >
        ← {data.job_title}
      </Link>

      <h1 className="mt-3 text-2xl font-semibold tracking-tight">
        Edit application
      </h1>

      <div className="mt-8">
        <ApplicationForm
          initial={data}
          submitLabel="Save changes"
          onSubmit={async (payload) => {
            // Status is excluded: it goes through the status endpoint so the
            // change is written to history. The backend rejects it here anyway.
            const { status: _status, ...rest } = payload as Record<string, unknown>;
            void _status;
            await update.mutateAsync(rest as ApplicationUpdate);
            toast.success("Changes saved");
            router.push(`/applications/${id}`);
          }}
        />
      </div>
    </main>
  );
}
