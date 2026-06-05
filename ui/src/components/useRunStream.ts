"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchRun, type LifecycleEvent, sseUrl, type RunSnapshot } from "@/lib/api";

export type AgentStatus = "idle" | "running" | "done" | "failed";
export type RunStatus = "connecting" | "running" | "done" | "failed" | "unknown";

const AGENT_IDS = ["global_critic", "printable_cv_critic", "strategy_agent"] as const;

function initialAgentStates(): Record<string, AgentStatus> {
  return Object.fromEntries(AGENT_IDS.map((id) => [id, "idle"]));
}

function applyEvent(
  current: Record<string, AgentStatus>,
  event: LifecycleEvent,
): Record<string, AgentStatus> {
  const agent = typeof event.payload.agent === "string" ? event.payload.agent : null;
  if (!agent) return current;

  if (event.type === "agent_started") {
    return { ...current, [agent]: "running" };
  }
  if (event.type === "agent_completed") {
    return { ...current, [agent]: "done" };
  }
  if (event.type === "run_failed") {
    return { ...current, [agent]: "failed" };
  }
  return current;
}

function statusFromSnapshot(snapshot: RunSnapshot): RunStatus {
  if (snapshot.status === "done") return "done";
  if (snapshot.status === "failed") return "failed";
  if (snapshot.status === "running") return "running";
  return "unknown";
}

function statusFromEvent(event: LifecycleEvent, current: RunStatus): RunStatus {
  if (event.type === "run_started") return "running";
  if (event.type === "run_completed") return "done";
  if (event.type === "run_failed") return "failed";
  return current === "connecting" ? "running" : current;
}

function eventKey(event: LifecycleEvent) {
  return `${event.timestamp}:${event.type}:${JSON.stringify(event.payload)}`;
}

function mergeEvent(current: LifecycleEvent[], event: LifecycleEvent) {
  const key = eventKey(event);
  if (current.some((item) => eventKey(item) === key)) return current;
  return [...current, event];
}

export function useRunStream(runId: string) {
  const [events, setEvents] = useState<LifecycleEvent[]>([]);
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null);
  const [status, setStatus] = useState<RunStatus>("connecting");
  const [agentStates, setAgentStates] = useState<Record<string, AgentStatus>>(initialAgentStates);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    let stream: EventSource | null = null;

    async function start() {
      try {
        const initial = await fetchRun(runId);
        if (!alive) return;

        setSnapshot(initial);
        setEvents(initial.events);
        setStatus(statusFromSnapshot(initial));
        setAgentStates(initial.events.reduce(applyEvent, initialAgentStates()));

        if (initial.status !== "running") return;

        stream = new EventSource(sseUrl(runId));
        stream.onopen = () => {
          if (alive) setConnected(true);
        };
        stream.onmessage = (message) => {
          if (!alive || !message.data) return;
          const event = JSON.parse(message.data) as LifecycleEvent;
          setEvents((current) => mergeEvent(current, event));
          setStatus((current) => statusFromEvent(event, current));
          setAgentStates((current) => applyEvent(current, event));
          if (event.type === "run_completed" || event.type === "run_failed") {
            stream?.close();
            setConnected(false);
          }
        };
        stream.onerror = () => {
          if (!alive) return;
          setConnected(false);
        };
      } catch (e) {
        if (!alive) return;
        setError(e instanceof Error ? e.message : String(e));
        setStatus("unknown");
      }
    }

    start();
    return () => {
      alive = false;
      stream?.close();
    };
  }, [runId]);

  const recentEvents = useMemo(() => events.slice(-8).reverse(), [events]);

  return {
    agentStates,
    connected,
    error,
    events,
    recentEvents,
    snapshot,
    status,
  };
}
