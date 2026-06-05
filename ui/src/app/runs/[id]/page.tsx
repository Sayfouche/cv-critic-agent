import { notFound } from "next/navigation";
import Link from "next/link";

type Params = Promise<{ id: string }>;

export default async function RunPage({ params }: { params: Params }) {
  const { id } = await params;
  if (!id || id.length < 6) notFound();

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-6 py-10 sm:px-10">
      <header className="flex items-center justify-between border-b border-[var(--border)] pb-4">
        <div>
          <Link
            href="/"
            className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] hover:text-[var(--foreground)]"
          >
            ← Back
          </Link>
          <h1 className="mt-1 text-lg font-medium">
            Run <span className="font-mono text-[var(--muted)]">{id}</span>
          </h1>
        </div>
      </header>

      <div className="flex flex-1 items-center justify-center py-24 text-sm text-[var(--muted)]">
        Live graph coming in commit 2 — for now the SSE stream is being recorded server-side.
      </div>
    </main>
  );
}
