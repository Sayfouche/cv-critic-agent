"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  adminAction,
  listAdminRequests,
  type AdminRequest,
  type AccessRequestStatus,
} from "@/lib/api";
import { clearAdminSession, readAdminSession } from "@/lib/admin-session";

const STATUS_FILTERS: { label: string; value: AccessRequestStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Pending", value: "pending" },
  { label: "Approved", value: "approved" },
  { label: "Consumed", value: "consumed" },
  { label: "Rejected", value: "rejected" },
  { label: "Revoked", value: "revoked" },
  { label: "Expired", value: "expired" },
];

export function AdminRequestsPanel() {
  const router = useRouter();
  const [filter, setFilter] = useState<AccessRequestStatus | "all">("all");
  const [items, setItems] = useState<AdminRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyIds, setBusyIds] = useState<Set<string>>(new Set());
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const token = readAdminSession();
    if (!token) {
      router.replace("/admin/login");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await listAdminRequests(
          token,
          filter === "all" ? undefined : filter,
        );
        if (cancelled) return;
        setItems(data.requests);
        setError(null);
      } catch (e) {
        if (cancelled) return;
        const msg = e instanceof Error ? e.message : String(e);
        if (msg === "unauthorized") {
          clearAdminSession();
          router.replace("/admin/login");
          return;
        }
        setError(msg);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [filter, refreshKey, router]);

  function refresh() {
    setRefreshKey((k) => k + 1);
  }

  async function doAction(id: string, action: "approve" | "reject" | "revoke") {
    const token = readAdminSession();
    if (!token) {
      router.replace("/admin/login");
      return;
    }
    setBusyIds((s) => new Set(s).add(id));
    try {
      await adminAction(token, id, action);
      refresh();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg === "unauthorized") {
        clearAdminSession();
        router.replace("/admin/login");
        return;
      }
      setError(msg);
    } finally {
      setBusyIds((s) => {
        const next = new Set(s);
        next.delete(id);
        return next;
      });
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`rounded-full border px-3 py-1 text-xs transition ${
              filter === f.value
                ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--foreground)]"
                : "border-[var(--border)] text-[var(--muted)] hover:border-[var(--accent)]/60"
            }`}
          >
            {f.label}
          </button>
        ))}
        <button
          onClick={refresh}
          className="ml-auto rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)] hover:border-[var(--accent)]/60"
        >
          Refresh
        </button>
        <button
          onClick={() => {
            clearAdminSession();
            router.replace("/admin/login");
          }}
          className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)] hover:border-red-500/60 hover:text-red-300"
        >
          Sign out
        </button>
      </div>

      {error ? (
        <p className="rounded-md border border-red-500/40 bg-red-500/5 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      ) : null}

      {items === null ? (
        <p className="text-sm text-[var(--muted)]">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">No requests in this view.</p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-[var(--border)]">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-[var(--surface)]/60 text-xs uppercase tracking-[0.12em] text-[var(--muted)]">
              <tr>
                <Th>Created</Th>
                <Th>Name</Th>
                <Th>Company</Th>
                <Th>Email</Th>
                <Th>Status</Th>
                <Th>Runs</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id} className="border-t border-[var(--border)] align-top">
                  <Td>
                    <time className="font-mono text-xs">
                      {new Date(r.created_at * 1000).toLocaleString()}
                    </time>
                  </Td>
                  <Td>
                    <div>{r.name}</div>
                    <div className="font-mono text-[10px] text-[var(--muted)]">
                      {r.id.slice(0, 8)}…
                    </div>
                  </Td>
                  <Td>{r.company || <span className="text-[var(--muted)]">—</span>}</Td>
                  <Td className="break-all">{r.email}</Td>
                  <Td>
                    <StatusPill status={r.status} />
                  </Td>
                  <Td>
                    {r.runs_used}/{r.runs_quota}
                  </Td>
                  <Td>
                    <RowActions
                      status={r.status}
                      busy={busyIds.has(r.id)}
                      onApprove={() => doAction(r.id, "approve")}
                      onReject={() => doAction(r.id, "reject")}
                      onRevoke={() => doAction(r.id, "revoke")}
                    />
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {items?.length ? (
        <details className="text-xs text-[var(--muted)]">
          <summary className="cursor-pointer">Show motives</summary>
          <ul className="mt-3 flex flex-col gap-3">
            {items.map((r) => (
              <li
                key={`${r.id}-motive`}
                className="rounded-md border border-[var(--border)] bg-[var(--surface)]/60 p-3"
              >
                <div className="text-[10px] uppercase tracking-[0.16em] text-[var(--muted)]">
                  {r.name} · {r.company || "—"}
                </div>
                <p className="mt-1 whitespace-pre-wrap text-sm text-[var(--foreground)]">
                  {r.motive}
                </p>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}

function StatusPill({ status }: { status: AccessRequestStatus }) {
  const styles: Record<AccessRequestStatus, string> = {
    pending: "border-amber-500/30 bg-amber-500/5 text-amber-300",
    approved: "border-emerald-500/30 bg-emerald-500/5 text-emerald-300",
    consumed: "border-sky-500/30 bg-sky-500/5 text-sky-300",
    rejected: "border-red-500/30 bg-red-500/5 text-red-300",
    revoked: "border-red-500/30 bg-red-500/5 text-red-300",
    expired: "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)]",
  };
  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs ${styles[status]}`}>
      {status}
    </span>
  );
}

function RowActions({
  status,
  busy,
  onApprove,
  onReject,
  onRevoke,
}: {
  status: AccessRequestStatus;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
  onRevoke: () => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {status === "pending" ? (
        <>
          <ActionButton onClick={onApprove} busy={busy} tone="ok">
            Approve
          </ActionButton>
          <ActionButton onClick={onReject} busy={busy} tone="warn">
            Reject
          </ActionButton>
        </>
      ) : null}
      {status === "approved" ? (
        <ActionButton onClick={onRevoke} busy={busy} tone="warn">
          Revoke
        </ActionButton>
      ) : null}
    </div>
  );
}

function ActionButton({
  onClick,
  busy,
  tone,
  children,
}: {
  onClick: () => void;
  busy: boolean;
  tone: "ok" | "warn";
  children: React.ReactNode;
}) {
  const toneClasses =
    tone === "ok"
      ? "border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10"
      : "border-amber-500/40 text-amber-300 hover:bg-amber-500/10";
  return (
    <button
      onClick={onClick}
      disabled={busy}
      className={`rounded-md border px-2 py-1 text-xs transition disabled:opacity-50 ${toneClasses}`}
    >
      {busy ? "…" : children}
    </button>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 font-medium">{children}</th>;
}
function Td({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <td className={`px-3 py-3 text-sm ${className ?? ""}`}>{children}</td>;
}
