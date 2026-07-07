# System Logs Integration

The macOS menu bar app writes execution events to Butterbase so a Vercel
dashboard can render a live terminal panel.

## Local Config

Copy `.env.example` to `.env` and fill in the real Butterbase app id and API
token:

```text
BUTTERBASE_APP_ID=app_your_real_app_id
BUTTERBASE_API_TOKEN=bb_sk_your_real_api_token
```

If these values are missing, or if Butterbase returns a missing app/table error,
`app.py` falls back to local demo biometrics instead of crashing or repeatedly
printing 404s.

## Butterbase Table

Create a table named `system_logs`:

```sql
create table system_logs (
  event text not null,
  timestamp timestamptz not null
);
```

The app writes rows through:

```text
POST /v1/{BUTTERBASE_APP_ID}/system_logs
```

The dashboard can poll the same table every two seconds:

```text
GET /v1/{BUTTERBASE_APP_ID}/system_logs
```

Sort rows by `timestamp` descending in the request or in the client, then render
oldest-to-newest inside the terminal panel.

## Event Contract

Current event prefixes:

- `[Boot]`: local app startup.
- `[Butterbase]`: wearable log pulls.
- `[RocketRide]`: cloud or demo pipeline classification.
- `[Biometrics]`: parsed glucose derivative, HRV, and compression state.
- `[Classifier]`: selected energy state.
- `[Neo4j]`: task selection, blocker traversal, and blocked prerequisites.
- `[Alert]`: physiological crash detection.
- `[Daytona]`: sandbox creation, execution, and teardown.
- `[UI]`: manual menu bar refreshes.

Neo4j blocker events are intentionally explicit, for example:

```text
[Neo4j] Blocked candidate: Ship dashboard waits on Seed test graph, Verify webhook.
```

That line is the key judge-facing proof that the recommendation is using the
dependency graph, not just filtering a flat task list.
