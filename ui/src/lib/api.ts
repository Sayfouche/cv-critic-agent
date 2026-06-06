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

export async function createRun(opts: { demoDelayMs?: number; mock: boolean; token?: string }) {
  const res = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(opts.token ? { "X-API-Token": opts.token } : {}),
    },
    body: JSON.stringify({ mock: opts.mock, demo_delay_ms: opts.demoDelayMs ?? 0 }),
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || `Failed to start run (${res.status})`);
  }
  return res.json() as Promise<{ run_id: string; mock: boolean; status: string }>;
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
