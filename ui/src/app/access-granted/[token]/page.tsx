import Link from "next/link";
import { notFound } from "next/navigation";
import { AccessGrantedLauncher } from "@/components/AccessGrantedLauncher";

type Params = Promise<{ token: string }>;

export const metadata = {
  title: "Access granted — CV Critic Agent",
};

export default async function AccessGrantedPage({ params }: { params: Params }) {
  const { token } = await params;
  if (!token || token.length < 10) notFound();

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-6 py-16 sm:px-10">
      <div className="space-y-3">
        <Link
          href="/"
          className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] hover:text-[var(--foreground)]"
        >
          ← Back
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Access granted
        </h1>
        <p className="text-sm leading-relaxed text-[var(--muted)]">
          Your session is valid for 24 hours. Launch a real run when you&apos;re ready —
          it will hit the LLM provider and consume one of your allotted slots.
        </p>
      </div>
      <AccessGrantedLauncher sessionToken={token} />
    </main>
  );
}
