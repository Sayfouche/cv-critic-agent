"use client";

import { useEffect, useState } from "react";
import { AgentGraph } from "@/components/AgentGraph";
import { useRunStream } from "@/components/useRunStream";
import { fetchGraph, type AgentNode } from "@/lib/api";

type RunDashboardProps = {
  runId: string;
};

function eventLabel(eventType: string) {
  return eventType.replaceAll("_", " ");
}

export function RunDashboard({ runId }: RunDashboardProps) {
  const [agents, setAgents] = useState<AgentNode[]>([]);
  const [graphError, setGraphError] = useState<string | null>(null);
  const stream = useRunStream(runId);

  useEffect(() => {
    fetchGraph()
      .then((data) => setAgents(data.agents))
      .catch((e) => setGraphError(e instanceof Error ? e.message : String(e)));
  }, []);

  const runtime =
    stream.events.length > 0
      ? `${stream.events.length} events`
      : stream.status === "connecting"
        ? "Connecting"
        : "No events";
  const streamLabel =
    stream.status === "done" ? "SSE complete" : stream.connected ? "SSE live" : "SSE replay";

  return (
    <section className="grid flex-1 grid-cols-1 gap-5 py-8 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)]/60 px-4 py-3 text-sm">
          <span className="font-mono uppercase text-[var(--muted)]">{stream.status}</span>
          <span className="h-4 w-px bg-[var(--border)]" />
          <span className="text-[var(--muted)]">{runtime}</span>
          <span className="h-4 w-px bg-[var(--border)]" />
          <span className={stream.connected || stream.status === "done" ? "text-emerald-300" : "text-[var(--muted)]"}>
            {streamLabel}
          </span>
          {stream.snapshot ? (
            <>
              <span className="h-4 w-px bg-[var(--border)]" />
              <span className="text-[var(--muted)]">
                {stream.snapshot.provider} / {stream.snapshot.model}
              </span>
            </>
          ) : null}
        </div>

        {graphError || stream.error ? (
          <div className="rounded-lg border border-red-400/40 bg-red-500/10 p-4 text-sm text-red-100">
            {graphError ?? stream.error}
          </div>
        ) : null}

        {agents.length ? (
          <AgentGraph agents={agents} states={stream.agentStates} />
        ) : (
          <div className="flex h-[460px] items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)]/60 text-sm text-[var(--muted)]">
            Loading graph
          </div>
        )}
      </div>

      <aside className="rounded-lg border border-[var(--border)] bg-[var(--surface)]/60 p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Event Stream</h2>
          <span className="font-mono text-xs text-[var(--muted)]">{stream.events.length}</span>
        </div>
        <div className="mt-4 space-y-3">
          {stream.recentEvents.map((event, index) => (
            <div key={`${event.timestamp}-${event.type}-${index}`} className="rounded-md bg-white/[0.03] px-3 py-2">
              <p className="text-xs font-medium capitalize">{eventLabel(event.type)}</p>
              <p className="mt-1 font-mono text-[11px] text-[var(--muted)]">
                {new Date(event.timestamp).toLocaleTimeString()}
              </p>
            </div>
          ))}
          {!stream.recentEvents.length ? (
            <p className="text-sm text-[var(--muted)]">Waiting for events</p>
          ) : null}
        </div>
      </aside>
    </section>
  );
}
