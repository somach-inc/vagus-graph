const invalidAppIds = new Set(["app_30r72zucnm70"]);

const defaultTasks = [
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

const demoRows = () => {
  const now = Date.now();
  return [
    ["[Boot] Butterbase-hosted Vagus Graph is live.", -14000],
    ["[Biometrics] Demo mode: dG/dt=0.0, HRV=55.0, compression_low=False.", -11000],
    ["[RocketRide] key-armed demo runtime selected gpt-5.5.", -8000],
    ["[Classifier] RocketRide evaluated energy as MEDIUM.", -6500],
    ["[Neo4j] Blocked candidate: Ship dashboard waits on Seed test graph.", -5000],
    ["[Daytona] Sandbox armed for low-energy crash branch.", -2000],
  ].map(([event, delta], index) => ({
    id: `demo-${index}`,
    event,
    timestamp: new Date(now + delta).toISOString(),
  }));
};

const state = {
  rows: [],
  source: "demo",
  tasks: loadTasks(),
};

const el = {
  terminal: document.querySelector("#terminal"),
  count: document.querySelector("#count"),
  updated: document.querySelector("#updated"),
  energy: document.querySelector("#energy"),
  blocker: document.querySelector("#blocker"),
  rocketride: document.querySelector("#rocketride"),
  source: document.querySelector("#source-pill"),
  dialog: document.querySelector("#config-dialog"),
  appId: document.querySelector("#app-id"),
  token: document.querySelector("#api-token"),
  taskList: document.querySelector("#task-list"),
  manualTaskForm: document.querySelector("#manual-task-form"),
  manualTaskTitle: document.querySelector("#manual-task-title"),
  remainingCount: document.querySelector("#remaining-count"),
  nextTask: document.querySelector("#next-task"),
};

function loadTasks() {
  const stored = localStorage.getItem("vagus_tasks");
  if (!stored) return defaultTasks;

  try {
    const tasks = JSON.parse(stored);
    return Array.isArray(tasks) ? tasks : defaultTasks;
  } catch {
    return defaultTasks;
  }
}

function saveTasks() {
  localStorage.setItem("vagus_tasks", JSON.stringify(state.tasks));
}

function formatTime(timestamp) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(timestamp));
}

function tone(event) {
  if (event.includes("[Alert]") || event.includes("CRASH")) return "danger";
  if (event.includes("[RocketRide]")) return "rocket";
  if (event.includes("[Neo4j]")) return "graph";
  if (event.includes("[Daytona]")) return "cloud";
  if (event.includes("[Biometrics]")) return "bio";
  return "default";
}

function deriveEnergy(rows) {
  const row = [...rows].reverse().find((item) => item.event.includes("[Classifier]"));
  if (!row) return "MEDIUM";
  if (row.event.includes("HIGH")) return "HIGH";
  if (row.event.includes("LOW")) return "LOW";
  return "MEDIUM";
}

function deriveBlocker(rows) {
  const row = [...rows].reverse().find((item) =>
    item.event.includes("[Neo4j] Blocked candidate"),
  );
  return row ? row.event.replace("[Neo4j] ", "") : "No active blocker event";
}

function normalizeRows(rows) {
  return rows
    .filter((row) => row.event)
    .map((row, index) => ({
      id: `${row.timestamp || "row"}-${index}`,
      event: row.event,
      timestamp: row.timestamp || new Date().toISOString(),
    }))
    .sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
}

function getConfig() {
  return {
    appId: localStorage.getItem("vagus_butterbase_app_id") || "",
    token: localStorage.getItem("vagus_butterbase_token") || "",
  };
}

async function fetchRows() {
  const { appId, token } = getConfig();

  if (!appId || !token || invalidAppIds.has(appId)) {
    state.source = "demo";
    return demoRows();
  }

  try {
    const response = await fetch(
      `https://api.butterbase.ai/v1/${appId}/system_logs`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );

    if (!response.ok) throw new Error(`Butterbase ${response.status}`);
    const payload = await response.json();
    const rows = Array.isArray(payload) ? payload : payload.data || [];
    state.source = "live";
    return normalizeRows(rows).slice(-120);
  } catch {
    state.source = "demo";
    return demoRows();
  }
}

function render(rows) {
  el.terminal.innerHTML = rows
    .map(
      (row) => `
        <div class="log-row tone-${tone(row.event)}">
          <time>${formatTime(row.timestamp)}</time>
          <span>${row.event}</span>
        </div>
      `,
    )
    .join("");

  el.count.textContent = `${rows.length} rows`;
  el.updated.textContent = formatTime(new Date().toISOString());
  el.energy.textContent = deriveEnergy(rows);
  el.blocker.textContent = deriveBlocker(rows);
  el.rocketride.textContent = rows.some((row) => row.event.includes("[RocketRide]"))
    ? "gpt-5.5"
    : "standby";
  el.source.textContent = state.source;
  el.source.className = `pill ${state.source === "live" ? "live" : "demo"}`;
  renderTasks();
}

function renderTasks() {
  const remaining = state.tasks.filter((task) => task.status !== "done");
  el.remainingCount.textContent = `${remaining.length} remaining`;
  el.nextTask.textContent = remaining[0]?.title || "All clear";

  el.taskList.innerHTML = state.tasks
    .map(
      (task) => `
        <article class="task-card task-${task.status}">
          <div>
            <span>${task.complexity}</span>
            <strong>${task.title}</strong>
          </div>
          <p>${task.detail}</p>
          <div class="task-actions">
            <small>${task.status}</small>
            ${
              task.status === "done"
                ? ""
                : `<button data-task-id="${task.id}" type="button">Done</button>`
            }
          </div>
        </article>
      `,
    )
    .join("");
}

async function refresh() {
  state.rows = await fetchRows();
  render(state.rows);
}

document.querySelector("#refresh-button").addEventListener("click", refresh);

document.querySelector("#config-button").addEventListener("click", () => {
  const config = getConfig();
  el.appId.value = config.appId;
  el.token.value = config.token;
  el.dialog.showModal();
});

document.querySelector("#save-config").addEventListener("click", () => {
  localStorage.setItem("vagus_butterbase_app_id", el.appId.value.trim());
  localStorage.setItem("vagus_butterbase_token", el.token.value.trim());
  refresh();
});

document.querySelector("#clear-config").addEventListener("click", () => {
  localStorage.removeItem("vagus_butterbase_app_id");
  localStorage.removeItem("vagus_butterbase_token");
  el.dialog.close();
  refresh();
});

el.manualTaskForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const title = el.manualTaskTitle.value.trim();
  if (!title) return;

  state.tasks = [
    {
      id: `manual-${Date.now()}`,
      title,
      complexity: "medium",
      status: "ready",
      detail: "Manual task added during demo.",
    },
    ...state.tasks,
  ];
  el.manualTaskTitle.value = "";
  saveTasks();
  renderTasks();
});

el.taskList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-task-id]");
  if (!button) return;

  state.tasks = state.tasks.map((task) =>
    task.id === button.dataset.taskId ? { ...task, status: "done" } : task,
  );
  saveTasks();
  renderTasks();
});

refresh();
setInterval(refresh, 2000);
