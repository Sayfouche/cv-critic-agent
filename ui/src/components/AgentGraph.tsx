"use client";

import { motion } from "framer-motion";
import { useMemo } from "react";
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
import type { AgentNode } from "@/lib/api";
import type { AgentStatus } from "@/components/useRunStream";

type AgentGraphProps = {
  agents: AgentNode[];
  states: Record<string, AgentStatus>;
};

type AgentNodeData = {
  label: string;
  status: AgentStatus;
};

const POSITIONS: Record<string, { x: number; y: number }> = {
  global_critic: { x: 80, y: 80 },
  printable_cv_critic: { x: 80, y: 280 },
  strategy_agent: { x: 560, y: 180 },
};

const STATUS_LABEL: Record<AgentStatus, string> = {
  idle: "Idle",
  running: "Running",
  done: "Done",
  failed: "Failed",
};

const STATUS_CLASS: Record<AgentStatus, string> = {
  idle: "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)]",
  running: "border-[var(--accent)] bg-[var(--surface-elevated)] text-[var(--foreground)] shadow-[0_0_32px_var(--accent-glow)]",
  done: "border-emerald-400/70 bg-emerald-400/10 text-emerald-100 shadow-[0_0_26px_rgba(52,211,153,0.22)]",
  failed: "border-red-400/80 bg-red-500/10 text-red-100 shadow-[0_0_26px_rgba(248,113,113,0.22)]",
};

function AgentGraphNode({ data }: NodeProps<AgentNodeData>) {
  const isRunning = data.status === "running";

  return (
    <motion.div
      animate={isRunning ? { scale: [1, 1.025, 1] } : { scale: 1 }}
      transition={{ duration: 1.3, repeat: isRunning ? Infinity : 0, ease: "easeInOut" }}
      className={`relative min-h-28 w-60 rounded-lg border px-5 py-4 backdrop-blur ${STATUS_CLASS[data.status]}`}
    >
      <Handle type="target" position={Position.Left} className="!border-0 !bg-[var(--accent)]" />
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-[var(--foreground)]">{data.label}</p>
          <p className="mt-1 font-mono text-xs uppercase text-current">{STATUS_LABEL[data.status]}</p>
        </div>
        <span className="mt-1 size-2 rounded-full bg-current shadow-[0_0_12px_currentColor]" />
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

export function AgentGraph({ agents, states }: AgentGraphProps) {
  const nodeTypes = useMemo(() => ({ agentNode: AgentGraphNode }), []);
  const nodes: Node<AgentNodeData>[] = agents.map((agent) => ({
    id: agent.id,
    type: "agentNode",
    position: POSITIONS[agent.id] ?? { x: 0, y: 0 },
    data: {
      label: agent.label,
      status: states[agent.id] ?? "idle",
    },
    draggable: false,
  }));

  const edges: Edge[] = agents.flatMap((agent) =>
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

  return (
    <div className="h-[460px] w-full overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)]/60">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.7}
        maxZoom={1.3}
        nodesDraggable={false}
        nodesConnectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(232,232,236,0.10)" gap={22} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
