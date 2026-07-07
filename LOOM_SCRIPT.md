# Loom Script

Target length: 2:30-3:30.

## Before recording

Open these:

- `https://vagus-db-two.butterbase.dev`
- iPhone Mirroring
- Stelo app
- Oura app
- iPhone Shortcuts app
- Neo4j Browser
- macOS menu bar with Vagus visible
- Terminal in `projects/vagus-graph`

Run:

```bash
cd /Users/carl/Downloads/somach/projects/vagus-graph
./venv/bin/python app.py
```

On the dashboard:

1. Click `Config`.
2. Enter `app_30r72zucrg4n`.
3. Enter the Butterbase token.
4. Save.

## Recording flow

### 0:00-0:20 camera on

"Hi, I’m Carl Kho. I studied computational sciences and cognitive neuroscience
at Minerva. This project is Vagus Graph: a wearable-driven task system that
uses live physiology to decide what kind of work I should do next."

Show CGM and Oura.

"This is my CGM and this is my Oura ring. The demo uses glucose trend and HRV as
rough signals for metabolic and autonomic state."

Turn camera off. Screen share stays on.

### 0:20-0:55 system overview

"The core idea is cognitive scaffolding. When physiology shifts, the software
doesn’t just show a chart. It changes the work queue."

Show iPhone Mirroring.

"I’m using iPhone Mirroring so this is visibly coming from the phone. Here are
the wearable sources: Stelo for glucose, Oura for recovery and HRV, and
Shortcuts for the demo trigger."

Point to dashboard top.

"The top panel is the actionable Task UI. It shows remaining tasks, lets me add
manual tasks, and marks which tasks are ready, blocked, or reserved for low
energy."

Point to graph/logs.

"Under that is the causal loop. The arrows matter: iPhone Shortcut writes to
Butterbase, the Mac agent polls the row, RocketRide classifies energy with a
GPT-5.5 policy, Neo4j checks task blockers, and the menu bar plus dashboard
react."

### 0:55-1:35 live trigger

Tap `Normal` Shortcut.

"I’m tapping the Normal Shortcut. That writes a biometric row to Butterbase."

Wait for dashboard terminal.

"The dashboard polls every two seconds. The Mac agent polls every ten seconds,
so full loop latency is usually a few seconds, worst case one poll cycle."

Point to menu bar.

"The menu bar mirrors the state so I don’t have to context switch into a full
app."

### 1:35-2:15 crash trigger

Tap `Crash` Shortcut.

"Now I’m forcing a low-energy state. The system sees the biometric change,
RocketRide classifies it, then Neo4j checks what work is appropriate."

Point to logs.

"The important part is the blocker reasoning. It’s not a flat to-do list. A task
can look easy but still be blocked by setup, credentials, or a prior task."

Switch briefly to Neo4j Browser.

"This is the same idea in Neo4j Browser. Tasks are nodes, and `BLOCKS`
relationships encode prerequisites. The app only recommends a task when its
blocking prerequisites are completed."

If Daytona starts:

"On the crash branch, Daytona spins up a sandbox to run verification away from
my local CPU and then tears it down."

### 2:15-2:50 recovery and close

Tap `Recovery` Shortcut.

"Finally I send a recovery row. The dashboard, task UI, and menu bar settle back
to a safer recommendation."

Close with:

"The long-term version is a personal cognitive prosthetic: wearable logs become
a task graph, the task graph becomes a live recommendation, and the interface
stays lightweight enough to guide work without interrupting it."

## If live data stalls

Say this and keep moving:

"The dashboard has a demo fallback so judges can still see the complete loop.
The live table is the same path; the fallback only protects the video from
network or Shortcut timing."

Then click Refresh, show Task UI, and explain the architecture.

## Screen layout

Preferred one-shot layout:

1. Left side: Butterbase dashboard.
2. Right/top: iPhone Mirroring for Stelo, Oura, and Shortcut taps.
3. Quick tab switch: Neo4j Browser for the `BLOCKS` graph.
4. macOS menu bar remains visible at the top the whole time.

Do not hide the menu bar in Loom. The menu bar is the ambient interface proof.

## Lines to avoid

- Do not over-explain every sponsor.
- Do not say "AI tells me what to do."
- Say "recommends work based on physiological state and task blockers."
- Do not mention sensitive keys or tokens.
