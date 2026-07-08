# Vagus Graph at HackwithBay

## What We Built

At HackwithBay, we built **Vagus Graph**, an interactive productivity system that turns live physiological state into a practical next-action recommendation. A native iPhone Shortcut reads biometric signals from the user's phone and wearable stack, Butterbase stores the incoming telemetry, RocketRide Cloud classifies the user's energy level through an LLM pipeline, and Neo4j Aura selects the right next task by traversing explicit task blockers. The result is not just a dashboard and not just a to-do list; it is a closed loop between body state, cognitive capacity, and graph-aware work planning.

## Architecture

The system starts with physical ingestion. An iPhone Shortcut queries raw biometric samples from on-device health data sources, including CGM glucose readings and recovery signals such as HRV. The Shortcut posts that telemetry over HTTPS into Butterbase, where Postgres tables preserve both the raw wearable rows and the state transitions produced later in the loop.

```text
iPhone Shortcut
  -> Butterbase Postgres wearable_logs
  -> RocketRide Cloud managed API gateway
  -> LLM energy/focus classification
  -> Neo4j Aura blocker traversal
  -> Butterbase Postgres system_logs / task state
  -> Next.js dashboard + macOS status bar app
  -> optional Daytona sandbox branch
```

RocketRide Cloud sits in the middle as the managed API gateway. Both the local macOS status bar app and the web dashboard can use the same endpoint, which means the classification policy can evolve in one place. The pipeline evaluates glucose rate-of-change, autonomic stress signals, and task complexity, then returns a clean state such as high focus, medium energy, or low-energy recovery mode.

From there, Neo4j Aura turns the recommendation into a graph problem. Tasks are nodes. Dependencies are directed `[:BLOCKS]` relationships. A task is only eligible if its blockers are completed, which prevents the system from recommending "easy" tasks that are actually impossible because a parent task is still open.

```cypher
MATCH (blocking:Task)-[:BLOCKS]->(task:Task)
RETURN blocking, task
```

The selected state, task, and execution trace are written back to Butterbase. The Next.js dashboard reads those records to show the live Task UI, the blocker graph, and a terminal-style system log panel. The macOS menu bar app shows the same recommendation in the user's peripheral vision, where it can guide action without forcing another context switch.

## Technical Challenges

The first challenge was unifying the pipeline behind a single managed cloud API gateway. A naive implementation would duplicate biological evaluation and graph querying logic inside the Mac script and the web app. That would make every prompt tweak, threshold change, or classification update require multiple redeployments. RocketRide Cloud gave the system one shared intelligence layer, so one update benefits both clients.

The second challenge was real-time observability across three disjoint environments: the iPhone Shortcut, the local Mac Python app, and Daytona cloud sandboxes. Those runtimes do not naturally share stdout, but the demo needed to feel alive and auditable. We solved that by treating logs as application data. Each environment writes structured events into a Butterbase `system_logs` table, and the dashboard polls every two seconds to render one live terminal panel.

```sql
system_logs (
  id uuid primary key,
  timestamp timestamptz default now(),
  event text not null
)
```

The third challenge was making the graph genuinely meaningful. We did not want a to-do list with a database behind it. We wanted recommendations to respect task topology. Modeling blockers as `[:BLOCKS]` relationships lets the app explain why a task is unavailable, not merely hide it. The graph UI visually emphasizes blocker paths so judges and collaborators can see the reasoning structure rather than only the final suggestion.

The final challenge was classification itself. Subjective energy and focus are noisy. A glucose value can look normal while its derivative signals an imminent crash; HRV can imply recovery debt even when the user feels motivated. The LLM policy layer gives us a flexible way to combine crash detection, focus profiling, and task complexity scoring into a state that is useful enough to drive recommendations.

## Stack

- **iOS Shortcuts** for live phone-triggered biometric writes.
- **Python** and `rumps` for the macOS status bar app.
- **Butterbase Postgres** for wearable logs, system logs, and shared state.
- **RocketRide Cloud** as the unified managed LLM API gateway.
- **Neo4j Aura** for task dependency modeling and blocker traversal.
- **Daytona sandboxes** for isolated cloud execution branches.
- **Next.js + Tailwind on Vercel** for the web dashboard.

## What's Next

Vagus Graph points toward the broader Somach.life thesis: cognitive scaffolding should help people act with their bodies, not against them. The next version will expand wearable integrations, learn personal baselines over time, improve task complexity scoring, and build a long-term memory layer that can adapt the task graph as the system learns which work patterns actually help the user stay healthy and effective.
