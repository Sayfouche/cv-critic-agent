"use client";

import { motion } from "framer-motion";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";
import type { AgentNode, LifecycleEvent } from "@/lib/api";
import type { AgentStatus } from "@/components/useRunStream";

type AgentGraphProps = {
  agents: AgentNode[];
  events: LifecycleEvent[];
  states: Record<string, AgentStatus>;
};

type AgentNodeData = {
  label: string;
  status: AgentStatus;
};

type ReportNodeData = {
  label: string;
  size: number | null;
  status: "pending" | "written";
};

type GraphNodeData = AgentNodeData | ReportNodeData;

const POSITIONS: Record<string, { x: number; y: number }> = {
  global_critic: { x: 48, y: 80 },
  printable_cv_critic: { x: 48, y: 292 },
  strategy_agent: { x: 372, y: 184 },
  report_global: { x: 760, y: 72 },
  "report_printable-cv": { x: 760, y: 214 },
  report_strategy: { x: 760, y: 356 },
  report_summary: { x: 1008, y: 220 },
};

const REPORT_ARTIFACTS = [
  { slug: "global", label: "global.md", agent: "global_critic" },
  { slug: "printable-cv", label: "printable-cv.md", agent: "printable_cv_critic" },
  { slug: "strategy", label: "strategy.md", agent: "strategy_agent" },
  { slug: "summary", label: "summary.md", agent: "strategy_agent" },
];

const STATUS_LABEL: Record<AgentStatus, string> = {
  idle: "Idle",
  running: "Running",
  done: "Done",
  failed: "Failed",
};

const STATUS_CLASS: Record<AgentStatus, string> = {
  idle: "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)]",
  running:
    "border-[var(--accent)] bg-[var(--surface-elevated)] text-[var(--foreground)] shadow-[0_0_32px_var(--accent-glow)]",
  done: "border-emerald-400/70 bg-emerald-400/10 text-emerald-100 shadow-[0_0_26px_rgba(52,211,153,0.22)]",
  failed: "border-red-400/80 bg-red-500/10 text-red-100 shadow-[0_0_26px_rgba(248,113,113,0.22)]",
};

function formatBytes(size: number | null) {
  if (size === null) return "--";
  if (size < 1024) return `${size} B`;
  return `${(size / 1024).toFixed(1)} KB`;
}

function AgentGraphNode({ data }: NodeProps<AgentNodeData>) {
  const isRunning = data.status === "running";

  return (
    <motion.div
      animate={isRunning ? { scale: [1, 1.025, 1] } : { scale: 1 }}
      transition={{ duration: 1.3, repeat: isRunning ? Infinity : 0, ease: "easeInOut" }}
      className={`relative min-h-32 w-[300px] overflow-hidden rounded-lg border px-5 py-4 backdrop-blur ${STATUS_CLASS[data.status]}`}
    >
      <Handle type="target" position={Position.Left} className="!border-0 !bg-[var(--accent)]" />
      <div className="absolute inset-x-0 top-0 h-1 bg-[var(--accent)] opacity-80" />
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-[var(--muted)]">agent task</p>
          <p className="text-sm font-semibold text-[var(--foreground)]">{data.label}</p>
          <p className="mt-1 font-mono text-xs uppercase text-current">{STATUS_LABEL[data.status]}</p>
        </div>
        <span className="rounded-md border border-white/10 bg-white/[0.06] px-2 py-1 font-mono text-[10px] uppercase text-current">
          {data.status}
        </span>
      </div>
      <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white/10">
        <motion.div
          className="h-full rounded-full bg-current"
          animate={isRunning ? { x: ["-100%", "100%"] } : { x: data.status === "done" ? "0%" : "-100%" }}
          transition={{ duration: 1.1, repeat: isRunning ? Infinity : 0, ease: "easeInOut" }}
        />
      </div>
      <Handle type="source" position={Position.Right} className="!border-0 !bg-[var(--accent)]" />
    </motion.div>
  );
}

function ReportGraphNode({ data }: NodeProps<ReportNodeData>) {
  const written = data.status === "written";
  return (
    <motion.div
      animate={written ? { opacity: 1, scale: 1 } : { opacity: 0.66, scale: 0.96 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="relative flex w-[170px] flex-col items-center gap-2 font-mono text-xs"
    >
      <Handle type="target" position={Position.Left} className="!left-2 !border-0 !bg-cyan-300" />
      <div
        className={`relative flex h-28 w-20 flex-col justify-between overflow-hidden rounded-sm border px-2.5 py-2 shadow-[0_16px_32px_rgba(0,0,0,0.22)] ${
          written
            ? "border-cyan-300/75 bg-cyan-300/10 text-cyan-100"
            : "border-slate-500/40 bg-slate-900/70 text-[var(--muted)]"
        }`}
      >
        <div
          className={`absolute right-0 top-0 h-0 w-0 border-l-[20px] border-t-[20px] border-l-transparent ${
            written ? "border-t-cyan-300/70" : "border-t-slate-500/60"
          }`}
        />
        <div
          className={`absolute right-[1px] top-[1px] h-0 w-0 border-l-[16px] border-t-[16px] border-l-transparent ${
            written ? "border-t-[#082f36]" : "border-t-[#0f172a]"
          }`}
        />
        <div className="flex items-center justify-between">
          <span className={`size-2 rounded-full ${written ? "bg-cyan-300 shadow-[0_0_12px_rgb(103,232,249)]" : "bg-slate-500"}`} />
          <span className="rounded border border-current/25 px-1 text-[9px] uppercase">md</span>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-[0.12em]">{written ? "written" : "pending"}</p>
          <p className="mt-1 text-[10px]">{formatBytes(data.size)}</p>
        </div>
      </div>
      <p className="w-28 truncate text-center text-[11px] text-[var(--foreground)]">{data.label}</p>
    </motion.div>
  );
}

const NODE_TYPES = { agentNode: AgentGraphNode, reportNode: ReportGraphNode };
const PRO_OPTIONS = { hideAttribution: true };

function writtenReports(events: LifecycleEvent[]) {
  const reports = new Map<string, number>();
  for (const event of events) {
    if (event.type !== "file_written") continue;
    const slug = typeof event.payload.slug === "string" ? event.payload.slug : "";
    const size = typeof event.payload.size === "number" ? event.payload.size : 0;
    reports.set(slug, size);
  }
  return reports;
}

export function AgentGraph({ agents, events, states }: AgentGraphProps) {
  const reports = writtenReports(events);
  const agentNodes: Node<GraphNodeData>[] = agents.map((agent) => ({
    id: agent.id,
    type: "agentNode",
    position: POSITIONS[agent.id] ?? { x: 0, y: 0 },
    data: {
      label: agent.label,
      status: states[agent.id] ?? "idle",
    },
    draggable: false,
  }));

  const reportNodes: Node<GraphNodeData>[] = REPORT_ARTIFACTS.map((report) => {
    const size = reports.get(report.slug) ?? null;
    return {
      id: `report_${report.slug}`,
      type: "reportNode",
      position: POSITIONS[`report_${report.slug}`] ?? { x: 0, y: 0 },
      data: {
        label: report.label,
        size,
        status: size === null ? "pending" : "written",
      },
      draggable: false,
    };
  });

  const dependencyEdges: Edge[] = agents.flatMap((agent) =>
    agent.depends_on.map((source) => {
      const sourceDone = states[source] === "done";
      const targetRunning = states[agent.id] === "running";
      return {
        id: `${source}-${agent.id}`,
        source,
        target: agent.id,
        animated: sourceDone || targetRunning,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: {
          stroke: sourceDone || targetRunning ? "var(--accent)" : "var(--border)",
          strokeWidth: sourceDone || targetRunning ? 2 : 1.4,
        },
      };
    }),
  );

  const reportEdges: Edge[] = REPORT_ARTIFACTS.map((report) => {
    const written = reports.has(report.slug);
    return {
      id: `${report.agent}-report-${report.slug}`,
      source: report.agent,
      target: `report_${report.slug}`,
      animated: written,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: {
        stroke: written ? "rgb(103 232 249)" : "var(--border)",
        strokeDasharray: written ? undefined : "5 5",
        strokeWidth: written ? 2 : 1.3,
      },
    };
  });

  return (
    <div className="overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)]/60">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] px-4 py-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--muted)]">execution canvas</p>
          <p className="mt-1 text-sm text-[var(--foreground)]">Agents on the left, generated Markdown artifacts on the right.</p>
        </div>
        <div className="flex flex-wrap items-center gap-4 font-mono text-[11px] uppercase text-[var(--muted)]">
          <span className="flex items-center gap-2">
            <span className="h-2 w-8 rounded-full bg-[var(--accent)]" />
            task / dependency
          </span>
          <span className="flex items-center gap-2">
            <span className="h-2 w-8 rounded-full border border-cyan-300/70 bg-cyan-300/25" />
            file output
          </span>
        </div>
      </div>
      <div className="relative h-[560px] w-full overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(124,92,255,0.06),transparent_35%),radial-gradient(circle_at_top_right,rgba(103,232,249,0.06),transparent_35%)]" />
        <div className="pointer-events-none absolute inset-y-0 left-[58%] w-px border-l border-dashed border-[var(--border)]/80" />
        <div className="pointer-events-none absolute left-4 top-4 rounded-full border border-[var(--border)] bg-black/20 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--muted)]">
          execution
        </div>
        <div className="pointer-events-none absolute right-4 top-4 rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-cyan-100">
          artifacts
        </div>
        <ReactFlow
          nodes={[...agentNodes, ...reportNodes]}
          edges={[...dependencyEdges, ...reportEdges]}
          fitView
          minZoom={0.6}
          maxZoom={1.15}
          nodesDraggable={false}
          nodesConnectable={false}
          nodeTypes={NODE_TYPES}
          proOptions={PRO_OPTIONS}
          className="relative z-10"
        >
          <Background color="rgba(232,232,236,0.08)" gap={24} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  );
}
