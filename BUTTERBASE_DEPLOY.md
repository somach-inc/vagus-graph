# Butterbase Frontend Deploy

Butterbase frontend deployments serve static assets from Cloudflare Pages. This
project includes a sponsor-ready static dashboard in `butterbase-static/`.

## Package

```bash
npm run build:butterbase
```

The command creates:

```text
dist/vagus-graph-butterbase.zip
```

Upload that ZIP in Butterbase's frontend deployment flow.

## Schema

Apply the live demo tables before running `app.py`:

```bash
npx -y @butterbase/cli schema apply schemas/butterbase.json \
  --app app_30r72zucrg4n \
  --name vagus-demo-tables
```

## Demo modes

- With no config, the page shows demo RocketRide, Neo4j, and Daytona logs.
- With a real Butterbase app id and read token entered through the page Config
  dialog, the page polls `system_logs` every two seconds.

The static page stores entered Butterbase values only in browser `localStorage`.
Do not use a broad admin token for public demos; use a narrow read token if
Butterbase gives you one.
