"use client";

import { useMemo, useState } from "react";
import { fetchReport, fetchSource, type LifecycleEvent, type SourceItem } from "@/lib/api";

type RunSidePanelProps = {
  events: LifecycleEvent[];
  recentEvents: LifecycleEvent[];
  runId: string;
};

type PanelTab = "events" | "reports" | "sources";

type ReportItem = {
  slug: string;
  path: string;
  size: number;
};

const REPORTS = [
  { slug: "global", label: "Global" },
  { slug: "printable-cv", label: "Printable CV" },
  { slug: "strategy", label: "Strategy" },
  { slug: "summary", label: "Summary" },
];

function eventLabel(eventType: string) {
  return eventType.replaceAll("_", " ");
}

function sourceItems(events: LifecycleEvent[]) {
  const loaded = events.findLast((event) => event.type === "sources_loaded");
  const sources = loaded?.payload.sources;
  if (!Array.isArray(sources)) return [];
  return (sources as Array<Partial<SourceItem>>).map((source) => {
    const path = typeof source.path === "string" ? source.path : "";
    return {
      name: typeof source.name === "string" ? source.name : path.split("/").at(-1) ?? path,
      path,
      size: typeof source.size === "number" ? source.size : 0,
      exists: Boolean(source.exists),
    };
  });
}

function reportItems(events: LifecycleEvent[]) {
  const bySlug = new Map<string, ReportItem>();
  for (const event of events) {
    if (event.type !== "file_written") continue;
    const slug = typeof event.payload.slug === "string" ? event.payload.slug : null;
    const path = typeof event.payload.path === "string" ? event.payload.path : "";
    const size = typeof event.payload.size === "number" ? event.payload.size : 0;
    if (slug && REPORTS.some((report) => report.slug === slug)) {
      bySlug.set(slug, { slug, path, size });
    }
  }
  return bySlug;
}

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`;
  return `${(size / 1024).toFixed(1)} KB`;
}

export function RunSidePanel({ events, recentEvents, runId }: RunSidePanelProps) {
  const [tab, setTab] = useState<PanelTab>("events");
  const [previewTitle, setPreviewTitle] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sources = useMemo(() => sourceItems(events), [events]);
  const reports = useMemo(() => reportItems(events), [events]);

  async function openReport(slug: string, label: string) {
    setTab("reports");
    setLoading(true);
    setError(null);
    try {
      setPreviewTitle(`${label}.md`);
      setPreview(await fetchReport(runId, slug));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function openSource(source: SourceItem) {
    setTab("sources");
    setLoading(true);
    setError(null);
    try {
      setPreviewTitle(source.name);
      setPreview(await fetchSource(source.name));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <aside className="flex min-h-[460px] flex-col rounded-lg border border-[var(--border)] bg-[var(--surface)]/60">
      <div className="grid grid-cols-3 border-b border-[var(--border)] text-xs">
        {(["events", "reports", "sources"] as PanelTab[]).map((item) => (
          <button
            key={item}
            onClick={() => setTab(item)}
            className={`h-11 border-r border-[var(--border)] font-mono uppercase last:border-r-0 ${
              tab === item ? "bg-white/[0.06] text-[var(--foreground)]" : "text-[var(--muted)]"
            }`}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {tab === "events" ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Event Stream</h2>
              <span className="font-mono text-xs text-[var(--muted)]">{events.length}</span>
            </div>
            {recentEvents.map((event, index) => (
              <div key={`${event.timestamp}-${event.type}-${index}`} className="rounded-md bg-white/[0.03] px-3 py-2">
                <p className="text-xs font-medium capitalize">{eventLabel(event.type)}</p>
                <p className="mt-1 font-mono text-[11px] text-[var(--muted)]">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </p>
              </div>
            ))}
            {!recentEvents.length ? <p className="text-sm text-[var(--muted)]">Waiting for events</p> : null}
          </div>
        ) : null}

        {tab === "reports" ? (
          <div className="space-y-3">
            {REPORTS.map((report) => {
              const item = reports.get(report.slug);
              return (
                <button
                  key={report.slug}
                  onClick={() => openReport(report.slug, report.label)}
                  disabled={!item}
                  className="flex w-full items-center justify-between rounded-md border border-[var(--border)] bg-white/[0.03] px-3 py-2 text-left text-sm disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <span>{report.label}</span>
                  <span className="font-mono text-xs text-[var(--muted)]">
                    {item ? formatBytes(item.size) : "pending"}
                  </span>
                </button>
              );
            })}
          </div>
        ) : null}

        {tab === "sources" ? (
          <div className="space-y-3">
            {sources.map((source) => (
              <button
                key={source.path}
                onClick={() => openSource(source)}
                className="w-full rounded-md border border-[var(--border)] bg-white/[0.03] px-3 py-2 text-left"
              >
                <span className="block text-sm">{source.name}</span>
                <span className="mt-1 block font-mono text-xs text-[var(--muted)]">{formatBytes(source.size)}</span>
              </button>
            ))}
            {!sources.length ? <p className="text-sm text-[var(--muted)]">Sources pending</p> : null}
          </div>
        ) : null}
      </div>

      {(previewTitle || loading || error) && tab !== "events" ? (
        <div className="max-h-64 border-t border-[var(--border)] p-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="truncate text-sm font-medium">{previewTitle}</p>
            {loading ? <span className="font-mono text-xs text-[var(--muted)]">loading</span> : null}
          </div>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          {preview ? (
            <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-black/30 p-3 text-xs leading-relaxed text-[var(--muted)]">
              {preview}
            </pre>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}
