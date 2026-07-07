# Vagus Graph: A Biodata-driven Task Manager

Vagus Graph is a closed-loop cognitive scaffolding demo. It takes live wearable
signals (blood glucose from Stelo by Dexcom and heartrate variability from Oura Ring 5), classifies cognitive energy, checks a Neo4j task dependency graph, and
updates both a Butterbase-hosted dashboard and a macOS menu bar app.

## Live demo

[![Watch the demo](https://cdn.loom.com/sessions/thumbnails/28a5c239df144343a2d14030c15c9dab-09f603b17cff625b.jpg)](https://www.loom.com/share/28a5c239df144343a2d14030c15c9dab)


- Dashboard: https://vagus-db-two.butterbase.dev
- Butterbase app: `app_30r72zucrg4n`
- Static deploy source: `butterbase-static/`
- Static deploy package: `dist/vagus-graph-butterbase.zip`

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

## Expected latency

| Step | Expected latency |
| :--- | ---: |
| Shortcut tap -> Butterbase row | 0.3-1.5s |
| Butterbase row -> dashboard | 0-2s |
| `app.py` polling cycle | up to 10s |
| RocketRide classification | 0.2-1.5s |
| Neo4j blocker query | <0.3s local |
| Daytona sandbox branch | 8-25s |
