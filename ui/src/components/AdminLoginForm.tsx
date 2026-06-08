"use client";

import { useState } from "react";
import { adminLogin } from "@/lib/api";

export function AdminLoginForm() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await adminLogin(email.trim());
      setSent(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <p className="rounded-md border border-emerald-500/30 bg-emerald-500/5 px-3 py-3 text-sm text-emerald-300">
        If that email matches the owner address, a magic link is on its way. Open it
        on this device to sign in.
      </p>
    );
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <label htmlFor="admin-email" className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">
        Email
      </label>
      <input
        id="admin-email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        autoComplete="email"
        className="w-full rounded-md border border-[var(--border)] bg-[var(--surface)]/60 px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent)]"
      />
      <button
        type="submit"
        disabled={!email.trim() || busy}
        className="inline-flex h-11 items-center justify-center rounded-full bg-[var(--accent)] px-5 text-sm font-medium text-white shadow-[0_0_30px_var(--accent-glow)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {busy ? "Sending…" : "Send magic link"}
      </button>
      {error ? <p className="text-xs text-red-400">{error}</p> : null}
    </form>
  );
}
