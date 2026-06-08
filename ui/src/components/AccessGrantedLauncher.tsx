"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createRun } from "@/lib/api";

export function AccessGrantedLauncher({ sessionToken }: { sessionToken: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function launch() {
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const res = await createRun({ mock: false, sessionToken });
      if (res.degraded) {
        setInfo(
          "Daily budget cap reached — the run was demoted to mock so you don't lose a slot. Try again tomorrow.",
        );
      }
      router.push(`/runs/${res.run_id}`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(humanizeError(msg));
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-[var(--border)] bg-[var(--surface)]/60 p-6">
      <button
        onClick={launch}
        disabled={busy}
        className="inline-flex h-12 items-center justify-center rounded-full bg-[var(--accent)] px-6 text-sm font-medium text-white shadow-[0_0_30px_var(--accent-glow)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {busy ? "Launching…" : "▶ Launch a real run"}
      </button>
      <p className="text-xs text-[var(--muted)]">
        Your session is bound to the IP you used to send the request. Hitting this
        from a different network will fail with 403.
      </p>
      {info ? (
        <p className="rounded-md border border-sky-500/30 bg-sky-500/5 px-3 py-2 text-xs text-sky-300">
          {info}
        </p>
      ) : null}
      {error ? (
        <p className="rounded-md border border-red-500/40 bg-red-500/5 px-3 py-2 text-xs text-red-300">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function humanizeError(raw: string): string {
  if (raw.includes("401")) {
    return "Invalid or expired session token. Sessions last 24 h; ask for a new one.";
  }
  if (raw.includes("Quota")) {
    return "You've used all your allotted real runs. Mock runs are still free.";
  }
  if (raw.includes("IP")) {
    return "Session bound to a different IP. Open the link from the same network you submitted from.";
  }
  if (raw.includes("403")) {
    return "Session no longer valid. Ask for a new one if you still need access.";
  }
  return `Could not start the run: ${raw}`;
}
