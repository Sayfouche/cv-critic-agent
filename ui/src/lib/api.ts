export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

export type AgentNode = {
  id: string;
  label: string;
  depends_on: string[];
};

export type SourceItem = {
  name: string;
  path: string;
  size: number;
  exists: boolean;
};

export type LifecycleEvent = {
  type: string;
  timestamp: string;
  payload: Record<string, unknown>;
};

export type RunSnapshot = {
  run_id: string;
  status: "running" | "done" | "failed";
  mock: boolean;
  provider: string;
  model: string;
  started_at: number;
  run_dir: string | null;
  error: string | null;
  events: LifecycleEvent[];
};

export type CreateRunResponse = {
  run_id: string;
  mock: boolean;
  status: string;
  degraded: boolean;
};

export async function createRun(opts: {
  demoDelayMs?: number;
  mock: boolean;
  sessionToken?: string;
}): Promise<CreateRunResponse> {
  const res = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(opts.sessionToken ? { "X-Session-Token": opts.sessionToken } : {}),
    },
    body: JSON.stringify({ mock: opts.mock, demo_delay_ms: opts.demoDelayMs ?? 0 }),
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || `Failed to start run (${res.status})`);
  }
  return res.json() as Promise<CreateRunResponse>;
}

export async function fetchGraph() {
  const res = await fetch(`${API_BASE}/api/graph`);
  if (!res.ok) throw new Error("Graph fetch failed");
  return res.json() as Promise<{ agents: AgentNode[] }>;
}

export async function fetchSources() {
  const res = await fetch(`${API_BASE}/api/sources`);
  if (!res.ok) throw new Error("Sources fetch failed");
  return res.json() as Promise<{ sources: SourceItem[] }>;
}

export async function fetchSource(name: string) {
  const res = await fetch(`${API_BASE}/api/sources/${encodeURIComponent(name)}`);
  if (!res.ok) throw new Error("Source fetch failed");
  return res.text();
}

export async function fetchRun(runId: string) {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Run fetch failed");
  return res.json() as Promise<RunSnapshot>;
}

export function sseUrl(runId: string) {
  return `${API_BASE}/api/runs/${runId}/events`;
}

export function reportUrl(runId: string, slug: string) {
  return `${API_BASE}/api/runs/${runId}/reports/${slug}`;
}

export async function fetchReport(runId: string, slug: string) {
  const res = await fetch(reportUrl(runId, slug), { cache: "no-store" });
  if (!res.ok) throw new Error("Report fetch failed");
  return res.text();
}

// ── Access request flow (Phase 5) ────────────────────────────────────────────

export type AccessRequestStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "consumed"
  | "expired"
  | "revoked";

export async function createAccessRequest(body: {
  name: string;
  company: string;
  email: string;
  motive: string;
  website?: string;
  turnstileToken?: string;
}) {
  const res = await fetch(`${API_BASE}/api/access-requests`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(body.turnstileToken
        ? { "cf-turnstile-response": body.turnstileToken }
        : {}),
    },
    body: JSON.stringify({
      name: body.name,
      company: body.company,
      email: body.email,
      motive: body.motive,
      website: body.website ?? "",
    }),
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || `Submission failed (${res.status})`);
  }
  return res.json() as Promise<{ id: string; status: AccessRequestStatus }>;
}

export async function fetchAccessStatus(id: string) {
  const res = await fetch(
    `${API_BASE}/api/access-requests/${encodeURIComponent(id)}/status`,
    { cache: "no-store" },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Status fetch failed (${res.status})`);
  return res.json() as Promise<{ id: string; status: AccessRequestStatus }>;
}

// ── Admin (magic link) ───────────────────────────────────────────────────────

export async function adminLogin(email: string) {
  const res = await fetch(`${API_BASE}/api/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) throw new Error(`Login failed (${res.status})`);
  return res.json() as Promise<{ sent: boolean }>;
}

export async function redeemMagicLink(token: string) {
  const res = await fetch(
    `${API_BASE}/api/admin/session/${encodeURIComponent(token)}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Magic link redemption failed (${res.status})`);
  return res.json() as Promise<{ session_token: string }>;
}

export type AdminRequest = {
  id: string;
  name: string;
  company: string;
  email: string;
  motive: string;
  status: AccessRequestStatus;
  created_at: number;
  decided_at: number | null;
  runs_used: number;
  runs_quota: number;
};

export async function listAdminRequests(
  adminSession: string,
  filterStatus?: AccessRequestStatus,
) {
  const url = new URL(`${API_BASE}/api/admin/requests`);
  if (filterStatus) url.searchParams.set("status", filterStatus);
  const res = await fetch(url.toString(), {
    headers: { "X-Admin-Session": adminSession },
    cache: "no-store",
  });
  if (res.status === 401) throw new Error("unauthorized");
  if (!res.ok) throw new Error(`List failed (${res.status})`);
  return res.json() as Promise<{ requests: AdminRequest[] }>;
}

export async function adminAction(
  adminSession: string,
  id: string,
  action: "approve" | "reject" | "revoke",
) {
  const res = await fetch(
    `${API_BASE}/api/admin/requests/${encodeURIComponent(id)}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Session": adminSession,
      },
      body: JSON.stringify({ action }),
    },
  );
  if (res.status === 401) throw new Error("unauthorized");
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || `Action failed (${res.status})`);
  }
  return res.json() as Promise<{ id: string; status: AccessRequestStatus }>;
}
