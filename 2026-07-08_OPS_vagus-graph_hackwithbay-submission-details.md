# HackwithBay Submission Details

## Project

- **Project title:** Vagus Graph
- **Company portfolio:** Somach.life
- **Repository:** `https://github.com/somach-inc/vagus-graph`
- **Monorepo source:** `https://github.com/somach-inc/somach/tree/main/projects/vagus-graph`
- **Deployed dashboard:** `https://vagus-db-two.butterbase.dev`
- **Primary story file:** `2026-07-07_RD_vagus-graph_hackwithbay-story.md`
- **Demo script:** `LOOM_SCRIPT.md`

## One-Line Summary

Vagus Graph is a closed-loop cognitive scaffolding app that reads live biometric state, classifies energy and focus through an LLM pipeline, and recommends the right next task using a Neo4j blocker graph.

## Submission Blurb

Vagus Graph connects physiology to productivity. An iPhone Shortcut writes wearable data into Butterbase, RocketRide Cloud evaluates the user's current energy state, Neo4j Aura checks which tasks are blocked or unblocked, and the result appears in both a macOS status bar app and a live Next.js dashboard. The system demonstrates a practical path toward health-aware cognitive scaffolding: not replacing human judgment, but helping people choose work that fits their current biological capacity.

## Technical Stack

```text
iOS Shortcuts
Python macOS menu bar app
Butterbase Postgres
RocketRide Cloud
Neo4j Aura
Daytona sandboxes
Next.js + Tailwind
```

## Demo Proof Points

- Show iPhone Mirroring with Stelo/Oura/Shortcuts visible.
- Trigger a Shortcut and watch Butterbase-backed logs update.
- Show the macOS status bar recommendation changing.
- Open Neo4j Browser to show `(:Task)-[:BLOCKS]->(:Task)` relationships.
- Explain that `system_logs` unifies events from phone, Mac, and cloud sandbox.
