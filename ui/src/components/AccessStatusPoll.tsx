"use client";

import { useEffect, useRef, useState } from "react";
import { fetchAccessStatus, type AccessRequestStatus } from "@/lib/api";

const POLL_INTERVAL_MS = 5_000;
const OWNER_EMAIL = process.env.NEXT_PUBLIC_OWNER_EMAIL ?? "mansour.saifallah@gmail.com";

export function AccessStatusPoll({ requestId }: { requestId: string }) {
  const [status, setStatus] = useState<AccessRequestStatus | "loading" | "missing">(
    "loading",
  );
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;
    let timer: number | undefined;

    async function tick() {
      if (cancelledRef.current) return;
      try {
        const res = await fetchAccessStatus(requestId);
        if (cancelledRef.current) return;
        if (res === null) {
          setStatus("missing");
          return; // 404 → stop polling
        }
        setStatus(res.status);
        setLastChecked(new Date());
        if (res.status === "pending") {
          timer = window.setTimeout(tick, POLL_INTERVAL_MS);
        }
      } catch {
        // Network blip: try again later.
        if (cancelledRef.current) return;
        timer = window.setTimeout(tick, POLL_INTERVAL_MS);
      }
    }
    tick();

    return () => {
      cancelledRef.current = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [requestId]);

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-[var(--border)] bg-[var(--surface)]/60 p-6">
      <StatusBlock status={status} ownerEmail={OWNER_EMAIL} />
      {lastChecked && status === "pending" ? (
        <p className="text-xs text-[var(--muted)]">
          Polling every 5 s · last check {lastChecked.toLocaleTimeString()}
        </p>
      ) : null}
    </div>
  );
}

function StatusBlock({
  status,
  ownerEmail,
}: {
  status: AccessRequestStatus | "loading" | "missing";
  ownerEmail: string;
}) {
  if (status === "loading") {
    return <Line label="Loading…" tone="muted" />;
  }
  if (status === "missing") {
    return (
      <>
        <Line label="Not found" tone="warn" />
        <p className="text-sm text-[var(--muted)]">
          This request ID doesn&apos;t exist (or it expired). Submit a new request from{" "}
          <a href="/access-request" className="text-[var(--accent)] underline">
            /access-request
          </a>
          .
        </p>
      </>
    );
  }
  if (status === "pending") {
    return (
      <>
        <Line label="Pending — waiting for review" tone="info" />
        <p className="text-sm text-[var(--muted)]">
          You should hear back within a day or two. You&apos;ll get an email at the
          address you provided with a session link if approved.
        </p>
        <p className="text-xs text-[var(--muted)]">
          Need to ping me directly?{" "}
          <a href={`mailto:${ownerEmail}`} className="underline">
            {ownerEmail}
          </a>
        </p>
      </>
    );
  }
  if (status === "approved") {
    return (
      <>
        <Line label="Approved ✅" tone="ok" />
        <p className="text-sm text-[var(--muted)]">
          Check your inbox for the session link. Sessions last 24 hours.
        </p>
      </>
    );
  }
  if (status === "consumed") {
    return (
      <>
        <Line label="Quota used" tone="info" />
        <p className="text-sm text-[var(--muted)]">
          You&apos;ve used all the real runs allocated to this session. Mock runs are
          still free and available on the home page.
        </p>
      </>
    );
  }
  if (status === "rejected") {
    return (
      <>
        <Line label="Rejected" tone="warn" />
        <p className="text-sm text-[var(--muted)]">
          The request was declined. You should have received an email — feel free to
          reply if you think there was a mix-up.
        </p>
      </>
    );
  }
  if (status === "expired") {
    return (
      <>
        <Line label="Expired" tone="muted" />
        <p className="text-sm text-[var(--muted)]">
          This request is past its TTL. Send a new one if you still want access.
        </p>
      </>
    );
  }
  if (status === "revoked") {
    return (
      <>
        <Line label="Revoked" tone="warn" />
        <p className="text-sm text-[var(--muted)]">Access was revoked.</p>
      </>
    );
  }
  return <Line label={status} tone="muted" />;
}

function Line({
  label,
  tone,
}: {
  label: string;
  tone: "ok" | "info" | "warn" | "muted";
}) {
  const toneClasses: Record<typeof tone, string> = {
    ok: "border-emerald-500/30 bg-emerald-500/5 text-emerald-300",
    info: "border-sky-500/30 bg-sky-500/5 text-sky-300",
    warn: "border-amber-500/30 bg-amber-500/5 text-amber-300",
    muted: "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)]",
  };
  return (
    <div className={`rounded-md border px-3 py-2 text-sm ${toneClasses[tone]}`}>
      {label}
    </div>
  );
}
