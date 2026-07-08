# Vagus Graph: Biodata-driven Task Manager

Vagus Graph is a closed-loop cognitive scaffolding demo. It takes live wearable
signals, classifies cognitive energy, checks a Neo4j task dependency graph, and
updates both a Butterbase-hosted dashboard and a macOS menu bar app.

## Live demo

- Dashboard: https://vagus-db-two.butterbase.dev
- Butterbase app: `app_30r72zucrg4n`
- Static deploy source: `butterbase-static/`
- Static deploy package: `dist/vagus-graph-butterbase.zip`

## Project records

Project narrative and audit-friendly records use ISO 8601 machine-sortable
filenames:

- `2026-07-07_RD_vagus-graph_hackwithbay-story.md`
- `2026-07-08_OPS_vagus-graph_machine-sortable-filing-prompt.md`
- `2026-07-08_OPS_vagus-graph_hackwithbay-submission-details.md`

## Causal loop

1. iPhone Shortcut writes biometrics to Butterbase `wearable_logs`.
2. `app.py` polls Butterbase, parses glucose and HRV, and estimates trend.
3. RocketRide adapter classifies energy with the `gpt-5.5` policy.
4. Neo4j filters tasks through `[:BLOCKS]` prerequisites.
5. The menu bar updates the current state and recommended task.
6. The dashboard polls `system_logs` every two seconds.
7. Low-energy states can trigger a Daytona sandbox verification branch.

## Run locally

```bash
cd /Users/carl/Downloads/somach/projects/vagus-graph
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python app.py
```

For the Next.js local dashboard:

```bash
npm run dev
```

For the Butterbase static package:

```bash
npm run build:butterbase
```

Deploy to Butterbase:

```bash
npx -y @butterbase/cli deploy butterbase-static \
  --app app_30r72zucrg4n \
  --framework static
```

## Tables

Apply schema:

```bash
npx -y @butterbase/cli schema apply schemas/butterbase.json \
  --app app_30r72zucrg4n \
  --name vagus-demo-tables
```

Core tables:

- `wearable_logs`: raw iPhone/HealthKit rows.
- `system_logs`: live execution log stream.
- `energy_states`: long-term classification records.
- `task_recommendations`: selected task and blocked reason.
- `sandbox_runs`: Daytona run metadata.

## Demo shortcuts

Use three iPhone Shortcuts rather than background automation:

- `Normal`: stable glucose/HRV.
- `Crash`: low HRV or glucose drop.
- `Recovery`: stable follow-up row.

Manual triggers are better than every-second automation because iOS Shortcuts
are not a reliable one-second background scheduler and CGM data is not a 1 Hz
signal.

## Expected latency

| Step | Expected latency |
| :--- | ---: |
| Shortcut tap -> Butterbase row | 0.3-1.5s |
| Butterbase row -> dashboard | 0-2s |
| `app.py` polling cycle | up to 10s |
| RocketRide classification | 0.2-1.5s |
| Neo4j blocker query | <0.3s local |
| Daytona sandbox branch | 8-25s |

## One-shot recording checklist

1. Open `https://vagus-db-two.butterbase.dev`.
2. Open iPhone Mirroring with Stelo, Oura, and Shortcuts ready.
3. Open Neo4j Browser for the task-blocker graph.
4. In dashboard Config, save app id and token.
5. Start `app.py`.
6. Put macOS menu bar in frame.
7. Start Loom with camera on.
8. Show CGM and Oura briefly.
9. Turn camera off.
10. Screen-share dashboard plus menu bar.
11. Tap `Normal`, then `Crash`, then `Recovery` Shortcut through iPhone Mirroring.
12. Switch briefly to Neo4j Browser to show `(:Task)-[:BLOCKS]->(:Task)`.
13. Narrate the logs and Task UI changes.
