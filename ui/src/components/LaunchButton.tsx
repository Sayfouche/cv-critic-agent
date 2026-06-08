"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createRun } from "@/lib/api";

export function LaunchButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const { run_id } = await createRun({ mock: true, demoDelayMs: 700 });
      router.push(`/runs/${run_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={start}
        disabled={busy}
        className="group relative inline-flex h-12 items-center justify-center gap-2 overflow-hidden rounded-full bg-[var(--accent)] px-6 text-sm font-medium text-white shadow-[0_0_30px_var(--accent-glow)] transition hover:brightness-110 disabled:opacity-60"
      >
        <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
        {busy ? "Starting…" : "▶ Mock run (instant)"}
      </button>
      {error ? (
        <p className="text-xs text-red-400">
          Could not start a run: {error}. Is the API running on{" "}
          <code className="rounded bg-[var(--surface)] px-1 py-0.5">{process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"}</code>?
        </p>
      ) : null}
    </div>
  );
}
