# Vagus Graph

Closed-loop cognitive augmentation prototype for physiological telemetry fusion, graph-backed task routing, macOS menu bar status, and low-energy Daytona sandbox automation.

## Files

- `sensor_engine.py`: polls mock Dexcom and Oura telemetry, filters compression lows, and posts cleaned wearable logs to Butterbase.
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
- `GRAPH_DATABASE_URL`: Neo4j Aura URI, such as `neo4j+s://<db-id>.databases.neo4j.io`.
- `GRAPH_DATABASE_PASSWORD`: Neo4j Aura password.
- `LLM_API_KEY`: LLM provider key used by Cognee.

## Optional environment keys

- `BUTTERBASE_API_KEY`: bearer token for Butterbase if the REST endpoint requires authentication.
- `GRAPH_DATABASE_PROVIDER`: defaults to `neo4j` in the example env.
- `GRAPH_DATABASE_USERNAME`: defaults to `neo4j` in the example env.

## Test

```bash
python -m unittest -v test_vagus.py
```
