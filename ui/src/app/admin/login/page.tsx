import Link from "next/link";
import { AdminLoginForm } from "@/components/AdminLoginForm";

export const metadata = {
  title: "Admin · login — CV Critic Agent",
};

export default function AdminLoginPage() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col gap-8 px-6 py-16 sm:px-10">
      <div className="space-y-2">
        <Link
          href="/"
          className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] hover:text-[var(--foreground)]"
        >
          ← Back
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight">Admin login</h1>
        <p className="text-sm text-[var(--muted)]">
          Magic-link auth. Drop your email and check your inbox.
        </p>
      </div>
      <AdminLoginForm />
    </main>
  );
}
