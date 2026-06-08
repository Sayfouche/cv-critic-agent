import Link from "next/link";
import { AdminRequestsPanel } from "@/components/AdminRequestsPanel";

export const metadata = {
  title: "Admin · access requests — CV Critic Agent",
};

export default function AdminRequestsPage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10 sm:px-10">
      <header className="flex items-center justify-between border-b border-[var(--border)] pb-4">
        <div>
          <Link
            href="/"
            className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] hover:text-[var(--foreground)]"
          >
            ← Back
          </Link>
          <h1 className="mt-1 text-lg font-medium">Access requests</h1>
        </div>
      </header>
      <AdminRequestsPanel />
    </main>
  );
}
