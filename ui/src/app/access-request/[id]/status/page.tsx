import Link from "next/link";
import { notFound } from "next/navigation";
import { AccessStatusPoll } from "@/components/AccessStatusPoll";

type Params = Promise<{ id: string }>;

export const metadata = {
  title: "Access request status — CV Critic Agent",
};

export default async function StatusPage({ params }: { params: Params }) {
  const { id } = await params;
  if (!id || id.length < 6) notFound();

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-6 py-16 sm:px-10">
      <div className="space-y-2">
        <Link
          href="/"
          className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] hover:text-[var(--foreground)]"
        >
          ← Back
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Request status
        </h1>
        <p className="font-mono text-xs text-[var(--muted)]">{id}</p>
      </div>
      <AccessStatusPoll requestId={id} />
    </main>
  );
}
