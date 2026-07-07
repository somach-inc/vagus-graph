"use client";

import {
  Activity,
  Apple,
  BrainCircuit,
  CircleDot,
  Cloud,
  Database,
  GitBranch,
  HeartPulse,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

type LogRow = {
  id: string;
  event: string;
  timestamp: string;
};

type LogsResponse = {
  source: "butterbase" | "demo";
  rows: LogRow[];
  error?: string;
};

type Task = {
  id: string;
  title: string;
  complexity: "low" | "medium" | "high";
  status: "ready" | "blocked" | "armed" | "done";
  detail: string;
};

const graphNodes = [
  { id: "iPhone", label: "iPhone", x: 8, y: 22, icon: Apple },
  { id: "Butterbase", label: "Butterbase", x: 32, y: 22, icon: Database },
  { id: "RocketRide", label: "RocketRide", x: 56, y: 22, icon: Sparkles },
  { id: "Classifier", label: "GPT-5.5 classifier", x: 80, y: 22, icon: BrainCircuit },
  { id: "Neo4j", label: "Neo4j blockers", x: 80, y: 50, icon: GitBranch },
  { id: "Menu", label: "macOS bar", x: 32, y: 68, icon: Activity },
  { id: "Daytona", label: "Daytona", x: 56, y: 68, icon: Cloud },
  { id: "Dashboard", label: "Dashboard", x: 80, y: 68, icon: TerminalSquare },
];

const graphEdges = [
  ["iPhone", "Butterbase"],
  ["Butterbase", "RocketRide"],
  ["RocketRide", "Classifier"],
  ["Classifier", "Neo4j"],
  ["Neo4j", "Menu"],
  ["Classifier", "Daytona"],
  ["Daytona", "Dashboard"],
  ["Butterbase", "Dashboard"],
];

const defaultTasks: Task[] = [
  {
    id: "verify-butterbase",
    title: "Verify Butterbase logs",
    complexity: "medium",
    status: "ready",
    detail: "Confirm wearable_logs and system_logs are both receiving rows.",
  },
  {
    id: "ship-dashboard",
    title: "Ship dashboard",
    complexity: "medium",
    status: "blocked",
    detail: "Blocked until Butterbase log stream is verified.",
  },
  {
    id: "run-daytona",
    title: "Run Daytona sandbox",
    complexity: "low",
    status: "armed",
    detail: "Triggers only on low energy or crash branch.",
  },
];

const latencySteps = [
  ["Shortcut tap", "0s"],
  ["Butterbase write", "0.3-1.5s"],
  ["Dashboard poll", "0-2s"],
  ["RocketRide classify", "0.2-1.5s"],
  ["Neo4j blocker query", "<0.3s local"],
  ["Daytona sandbox", "8-25s"],
];

const staticLogs: LogRow[] = [
  {
    id: "static-boot",
    event: "[Boot] Dashboard ready.",
    timestamp: "2026-07-07T00:00:00.000Z",
  },
  {
    id: "static-graph",
    event: "[Neo4j] Dependency graph loaded.",
    timestamp: "2026-07-07T00:00:03.000Z",
  },
  {
    id: "static-rocketride",
    event: "[RocketRide] Awaiting physiology stream with gpt-5.5.",
    timestamp: "2026-07-07T00:00:06.000Z",
  },
];

function formatTime(timestamp: string) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(timestamp));
}

function eventTone(event: string) {
  if (event.includes("[Alert]") || event.includes("CRASH")) return "danger";
  if (event.includes("[RocketRide]")) return "rocket";
  if (event.includes("[Neo4j]")) return "graph";
  if (event.includes("[Daytona]")) return "cloud";
  if (event.includes("[Biometrics]")) return "bio";
  return "default";
}

function deriveEnergy(rows: LogRow[]) {
  const classifier = [...rows]
    .reverse()
    .find((row) => row.event.includes("[Classifier]"));

  if (!classifier) return "MEDIUM";
  if (classifier.event.includes("HIGH")) return "HIGH";
  if (classifier.event.includes("LOW")) return "LOW";
  return "MEDIUM";
}

function deriveBlocker(rows: LogRow[]) {
  const blocker = [...rows]
    .reverse()
    .find((row) => row.event.includes("[Neo4j] Blocked candidate"));

  return blocker?.event.replace("[Neo4j] ", "") ?? "No active blocker event";
}

export function Dashboard() {
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [source, setSource] = useState<LogsResponse["source"]>("demo");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [tasks, setTasks] = useState<Task[]>(defaultTasks);
  const [manualTask, setManualTask] = useState("");

  async function refreshLogs() {
    setIsRefreshing(true);
    try {
      const response = await fetch("/api/system-logs", { cache: "no-store" });
      const payload = (await response.json()) as LogsResponse;
      setLogs(payload.rows);
      setSource(payload.source);
      setLastUpdated(new Date());
    } finally {
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    const storedTasks = window.localStorage.getItem("vagus_tasks");
    if (storedTasks) {
      try {
        setTasks(JSON.parse(storedTasks) as Task[]);
      } catch {
        setTasks(defaultTasks);
      }
    }
    refreshLogs();
    const interval = window.setInterval(refreshLogs, 2000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    window.localStorage.setItem("vagus_tasks", JSON.stringify(tasks));
  }, [tasks]);

  function addManualTask() {
    const title = manualTask.trim();
    if (!title) return;

    setTasks((current) => [
      {
        id: `manual-${Date.now()}`,
        title,
        complexity: "medium",
        status: "ready",
        detail: "Manual task added during demo.",
      },
      ...current,
    ]);
    setManualTask("");
  }

  function completeTask(taskId: string) {
    setTasks((current) =>
      current.map((task) =>
        task.id === taskId ? { ...task, status: "done" } : task,
      ),
    );
  }

  const terminalRows = logs.length ? logs : staticLogs;

  const energy = useMemo(() => deriveEnergy(terminalRows), [terminalRows]);
  const blocker = useMemo(() => deriveBlocker(terminalRows), [terminalRows]);
  const blockedCount = terminalRows.filter((row) =>
    row.event.includes("Blocked candidate"),
  ).length;
  const remainingTasks = tasks.filter((task) => task.status !== "done");

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Somach research console</p>
          <h1>Vagus Graph</h1>
        </div>
        <div className="top-actions">
          <div className={`source-pill source-${source}`}>
            <CircleDot size={16} />
            {source}
          </div>
          <button className="icon-button" onClick={refreshLogs} type="button">
            <RefreshCw size={18} className={isRefreshing ? "spin" : ""} />
          </button>
        </div>
      </header>

      <section className="task-section task-section-top">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Task UI</p>
            <h2>Recommended work queue</h2>
          </div>
          <ShieldCheck size={18} />
        </div>

        <div className="task-toolbar">
          <div>
            <span>{remainingTasks.length} remaining</span>
            <strong>{remainingTasks[0]?.title ?? "All clear"}</strong>
          </div>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              addManualTask();
            }}
          >
            <input
              aria-label="Manual task title"
              onChange={(event) => setManualTask(event.target.value)}
              placeholder="Add manual task..."
              value={manualTask}
            />
            <button type="submit">Add</button>
          </form>
        </div>

        <div className="task-grid">
          {tasks.map((task) => (
            <article className={`task-card task-${task.status}`} key={task.id}>
              <div>
                <span>{task.complexity}</span>
                <strong>{task.title}</strong>
              </div>
              <p>{task.detail}</p>
              <div className="task-actions">
                <small>{task.status}</small>
                {task.status !== "done" ? (
                  <button onClick={() => completeTask(task.id)} type="button">
                    Done
                  </button>
                ) : null}
              </div>
            </article>
          ))}

          <article className="latency-card">
            <div>
              <span>Demo latency</span>
              <strong>Shortcut to screen</strong>
            </div>
            <div className="latency-list">
              {latencySteps.map(([label, value]) => (
                <div key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section className="metrics-band" aria-label="System metrics">
        <div className="metric">
          <HeartPulse size={20} />
          <div>
            <span>Energy</span>
            <strong>{energy}</strong>
          </div>
        </div>
        <div className="metric">
          <GitBranch size={20} />
          <div>
            <span>Blockers</span>
            <strong>{blockedCount}</strong>
          </div>
        </div>
        <div className="metric wide">
          <ShieldCheck size={20} />
          <div>
            <span>Recommendation gate</span>
            <strong>{blocker}</strong>
          </div>
        </div>
        <div className="metric">
          <Zap size={20} />
          <div>
            <span>Polling</span>
            <strong>2s</strong>
          </div>
        </div>
      </section>

      <section className="workbench">
        <div className="graph-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Closed loop</p>
              <h2>Physiology to action</h2>
            </div>
            <Play size={18} />
          </div>

          <div className="graph-canvas">
            <svg className="edges" viewBox="0 0 100 90" preserveAspectRatio="none">
              <defs>
                <marker id="dashboard-arrow" markerHeight="7" markerWidth="7" orient="auto" refX="6" refY="3.5">
                  <path d="M0,0 L7,3.5 L0,7 Z" />
                </marker>
              </defs>
              {graphEdges.map(([from, to]) => {
                const a = graphNodes.find((node) => node.id === from);
                const b = graphNodes.find((node) => node.id === to);
                if (!a || !b) return null;
                return (
                  <line
                    key={`${from}-${to}`}
                    x1={a.x + 5}
                    y1={a.y + 5}
                    x2={b.x + 5}
                    y2={b.y + 5}
                  />
                );
              })}
            </svg>
            <span className="edge-label dashboard-l1">write row</span>
            <span className="edge-label dashboard-l2">classify</span>
            <span className="edge-label dashboard-l3">LLM policy</span>
            <span className="edge-label dashboard-l4">blockers</span>
            <span className="edge-label dashboard-l5">safe task</span>
            <span className="edge-label dashboard-l6">crash branch</span>

            {graphNodes.map((node) => {
              const Icon = node.icon;
              return (
                <div
                  className={`graph-node node-${node.id.toLowerCase()}`}
                  key={node.id}
                  style={{ left: `${node.x}%`, top: `${node.y}%` }}
                >
                  <Icon size={18} />
                  <span>{node.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        <aside className="terminal-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Live execution</p>
              <h2>System logs</h2>
            </div>
            <TerminalSquare size={18} />
          </div>

          <div className="terminal">
            {terminalRows.map((row) => (
              <div className={`log-row tone-${eventTone(row.event)}`} key={row.id}>
                <time>{formatTime(row.timestamp)}</time>
                <span>{row.event}</span>
              </div>
            ))}
          </div>

          <footer className="terminal-footer">
            <span>{lastUpdated ? formatTime(lastUpdated.toISOString()) : "--:--:--"}</span>
            <span>{terminalRows.length} rows</span>
          </footer>
        </aside>
      </section>

    </main>
  );
}
