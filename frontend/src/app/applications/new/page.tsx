"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { ApplicationForm } from "@/components/applications/application-form";
import { AppShell } from "@/components/layout/app-shell";
import { BackLink } from "@/components/ui/back-link";
import { useCreateApplication } from "@/lib/applications";
import type { ApplicationCreate } from "@/lib/types";

export default function NewApplicationPage() {
  return (
    <AppShell>
      <NewApplication />
    </AppShell>
  );
}

function NewApplication() {
  const router = useRouter();
  const create = useCreateApplication();

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <BackLink href="/applications">Applications</BackLink>

      <h1 className="display mt-4 text-[1.75rem] leading-tight">
        Add an application
      </h1>
      <p className="measure mt-2 text-muted-foreground">
        Only the company and job title are required — fill in the rest whenever
        you have it.
      </p>

      <div className="mt-8">
        <ApplicationForm
          submitLabel="Add application"
          onSubmit={async (payload) => {
            const created = await create.mutateAsync(payload as ApplicationCreate);
            toast.success("Application added");
            router.push(`/applications/${created.id}`);
          }}
        />
      </div>
    </main>
  );
}
