import { AccessRequestForm } from "@/components/AccessRequestForm";
import Link from "next/link";

export const metadata = {
  title: "Request real-run access — CV Critic Agent",
};

export default function AccessRequestPage() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-10 px-6 py-16 sm:px-10">
      <div className="space-y-3">
        <Link
          href="/"
          className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] hover:text-[var(--foreground)]"
        >
          ← Back
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Request real-run access
        </h1>
        <p className="text-sm leading-relaxed text-[var(--muted)]">
          Real runs hit the LLM provider and cost money, so they&apos;re gated by manual
          approval. Tell me who you are and why you&apos;d like one, and you&apos;ll get
          an email with a session link within a day or two. Mock runs stay free and
          instant — no need to fill this if you just want to see the workflow.
        </p>
      </div>
      <AccessRequestForm />
    </main>
  );
}
