# Vagus Graph

Closed-loop cognitive augmentation prototype for physiological telemetry fusion, graph-backed task routing, macOS menu bar status, and low-energy Daytona sandbox automation.

## Files

- `sensor_engine.py`: reads Stelo glucose from Apple Health export XML, polls Oura Cloud when configured, filters compression lows, and posts cleaned wearable logs to Butterbase.
- `app.py`: macOS menu bar app that polls RocketRide, updates cognitive state, and launches Daytona on low-energy states.
- `memory.py`: Cognee semantic memory integration backed by Neo4j Aura.
- `schema.cypher`: Neo4j Aura schema, seed graph shape, and state-aware task query.
- `test_vagus.py`: unit tests with mocked network and subprocess calls.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` before running live integrations.

## Required environment keys

- `ROCKETRIDE_SECRET`: RocketRide Cloud bearer token.
- `APPLE_HEALTH_EXPORT_XML`: absolute path to Apple Health `export.xml` containing Stelo blood-glucose records.
- `OURA_ACCESS_TOKEN`: Oura Cloud API OAuth access token with `daily` and relevant wearable scopes.
- `GRAPH_DATABASE_URL`: Neo4j Aura URI, such as `neo4j+s://<db-id>.databases.neo4j.io`.
- `GRAPH_DATABASE_PASSWORD`: Neo4j Aura password.
- `LLM_API_KEY`: LLM provider key used by Cognee.

## Optional environment keys

- `BUTTERBASE_API_KEY`: bearer token for Butterbase if the REST endpoint requires authentication.
- `OURA_IS_VERTICAL`: posture override for compression-low filtering. Oura Cloud does not expose real-time posture; use `false` for sleep/rest exports and `true` if you know the reading occurred upright.
- `GRAPH_DATABASE_PROVIDER`: defaults to `neo4j` in the example env.
- `GRAPH_DATABASE_USERNAME`: defaults to `neo4j` in the example env.

## Stelo via Apple Health

The Stelo app can write blood-glucose readings into Apple Health. Apple Health exports all data as XML, so this project reads the latest two `HKQuantityTypeIdentifierBloodGlucose` records from `export.xml`.

1. On iPhone, open Health.
2. Tap your profile picture or initials.
3. Tap Export All Health Data.
4. Share the export to your Mac with AirDrop or Files.
5. Unzip the export.
6. Find `apple_health_export/export.xml`.
7. Set the absolute path in `.env`:

```bash
APPLE_HEALTH_EXPORT_XML=/Users/carl/Downloads/apple_health_export/export.xml
```

## Oura

Oura Cloud API V2 uses OAuth2 bearer tokens. Create an Oura API application, authorize your own account, and put the access token in `.env`:

```bash
OURA_ACCESS_TOKEN=...
OURA_IS_VERTICAL=false
```

Oura Cloud can provide daily activity and sleep-derived HRV, but it does not provide true real-time body posture through the public API. The compression-low posture input is therefore an explicit override.

## Test

```bash
python -m unittest -v test_vagus.py
```
