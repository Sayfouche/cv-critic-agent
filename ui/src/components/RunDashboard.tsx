"use client";

import { useEffect, useState } from "react";
import { AgentGraph } from "@/components/AgentGraph";
import { RunSidePanel } from "@/components/RunSidePanel";
import { useRunStream } from "@/components/useRunStream";
import { fetchGraph, type AgentNode } from "@/lib/api";

type RunDashboardProps = {
  runId: string;
};

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
  const fileCount = stream.events.filter((event) => event.type === "file_written").length;

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
          <span className="h-4 w-px bg-[var(--border)]" />
          <span className="text-[var(--muted)]">{fileCount} files</span>
        </div>

        {graphError || stream.error ? (
          <div className="rounded-lg border border-red-400/40 bg-red-500/10 p-4 text-sm text-red-100">
            {graphError ?? stream.error}
          </div>
        ) : null}

        {agents.length ? (
          <AgentGraph agents={agents} events={stream.events} states={stream.agentStates} />
        ) : (
          <div className="flex h-[460px] items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)]/60 text-sm text-[var(--muted)]">
            Loading graph
          </div>
        )}
      </div>

      <RunSidePanel events={stream.events} recentEvents={stream.recentEvents} runId={runId} />
    </section>
  );
}
