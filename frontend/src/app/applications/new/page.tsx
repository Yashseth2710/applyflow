"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { ApplicationForm } from "@/components/applications/application-form";
import { AppShell } from "@/components/layout/app-shell";
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
      <Link
        href="/applications"
        className="text-sm text-muted-foreground hover:text-foreground"
      >
        ← Applications
      </Link>

      <h1 className="mt-3 text-2xl font-semibold tracking-tight">
        Add an application
      </h1>
      <p className="mt-1 text-sm text-muted-foreground">
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
