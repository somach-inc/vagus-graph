import sys
import os
from datetime import datetime, timezone

import rumps
from neo4j import GraphDatabase


def load_local_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


load_local_env()

# Local Neo4j connection
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password123")

BUTTERBASE_APP_ID = os.getenv("BUTTERBASE_APP_ID", "")
BUTTERBASE_API_TOKEN = os.getenv("BUTTERBASE_API_TOKEN", "")
BUTTERBASE_API_BASE = (
    f"https://api.butterbase.ai/v1/{BUTTERBASE_APP_ID}"
    if BUTTERBASE_APP_ID
    else ""
)
INVALID_BUTTERBASE_APP_IDS = {"app_30r72zucnm70"}
ROCKETRIDE_API_KEY = os.getenv("ROCKETRIDE_API_KEY", "")
ROCKETRIDE_PIPELINE_URL = os.getenv("ROCKETRIDE_PIPELINE_URL", "")
ROCKETRIDE_MODEL = os.getenv("ROCKETRIDE_MODEL", "gpt-5.5")

class VagusMenuBarApp(rumps.App):
    def __init__(self):
        super(VagusMenuBarApp, self).__init__("🧠 Vagus: Active")
        self.menu = ["Refresh Tasks", None]
        self.butterbase_enabled = bool(
            BUTTERBASE_APP_ID
            and BUTTERBASE_API_TOKEN
            and BUTTERBASE_APP_ID not in INVALID_BUTTERBASE_APP_IDS
        )
        self.butterbase_warning_printed = False

        self.log_event("[Boot] Initializing task database sync...")
        if self.butterbase_enabled:
            self.log_event(f"[Config] Butterbase app configured: {BUTTERBASE_APP_ID}.")
        else:
            self.log_event(
                "[Config] Butterbase is not configured; using local demo biometrics."
            )
        if ROCKETRIDE_API_KEY:
            self.log_event(
                f"[RocketRide] Runtime armed with model {ROCKETRIDE_MODEL}."
            )
        else:
            self.log_event(
                f"[RocketRide] Demo adapter active with model {ROCKETRIDE_MODEL}."
            )
        self.update_menu_tasks()

        # Initialize and start the timer programmatically
        # This keeps 'self' bound to the VagusMenuBarApp instance
        self.timer = rumps.Timer(self.run_biometric_loop, 10)
        self.timer.start()

        self.log_event("[Boot] Vagus Menu Bar Utility is fully active.")

    def log_event(self, event, stderr=False):
        stream = sys.stderr if stderr else sys.stdout
        print(event, file=stream)

        if not self.butterbase_enabled:
            return

        try:
            import requests

            headers = {
                "Authorization": f"Bearer {BUTTERBASE_API_TOKEN}",
                "Content-Type": "application/json",
            }
            payload = {
                "event": event,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            response = requests.post(
                f"{BUTTERBASE_API_BASE}/system_logs",
                headers=headers,
                json=payload,
                timeout=5,
            )
            if response.status_code >= 400:
                if response.status_code == 404:
                    self.butterbase_enabled = False
                print(
                    f"[Log Sink Warning] Butterbase system_logs returned "
                    f"{response.status_code}: {response.text}",
                    file=sys.stderr,
                )
        except Exception as e:
            print(f"[Log Sink Warning] Failed to write system log: {e}", file=sys.stderr)

    def warn_butterbase_unavailable(self, message):
        if not self.butterbase_warning_printed:
            self.butterbase_warning_printed = True
            self.log_event(message, stderr=True)

    def demo_biometrics(self):
        glucose_change = 0.0
        hrv = 55.0
        is_compression = False
        self.log_event(
            "[Biometrics] Demo mode: "
            f"dG/dt={glucose_change:.1f}, HRV={hrv:.1f}, "
            f"compression_low={is_compression}."
        )
        return glucose_change, hrv, is_compression

    def classify_energy_locally(self, glucose_change, hrv, is_compression):
        if is_compression:
            return "medium"
        if glucose_change < -12.0 or hrv < 35:
            return "low"
        if glucose_change > -2.0 and hrv > 60:
            return "high"
        return "medium"

    def run_rocketride_classification(self, glucose_change, hrv, is_compression):
        payload = {
            "model": ROCKETRIDE_MODEL,
            "inputs": {
                "glucose_change": glucose_change,
                "hrv": hrv,
                "is_compression_low": is_compression,
            },
            "success_criteria": {
                "output": "energy_level",
                "allowed_values": ["low", "medium", "high"],
            },
        }

        if ROCKETRIDE_API_KEY and ROCKETRIDE_PIPELINE_URL:
            try:
                import requests

                self.log_event(
                    f"[RocketRide] Calling cloud pipeline with {ROCKETRIDE_MODEL}."
                )
                response = requests.post(
                    ROCKETRIDE_PIPELINE_URL,
                    headers={
                        "Authorization": f"Bearer {ROCKETRIDE_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10,
                )
                if response.status_code < 400:
                    result = response.json()
                    energy = (
                        result.get("energy_level")
                        or result.get("energy")
                        or result.get("classification")
                    )
                    if energy in {"low", "medium", "high"}:
                        self.log_event(
                            "[RocketRide] Cloud classified energy state as "
                            f"{energy.upper()}."
                        )
                        return energy

                self.log_event(
                    "[RocketRide] Cloud pipeline returned unusable response; "
                    "using local demo classifier.",
                    stderr=True,
                )
            except Exception as e:
                self.log_event(
                    f"[RocketRide] Cloud call failed: {e}; using local demo classifier.",
                    stderr=True,
                )

        energy = self.classify_energy_locally(glucose_change, hrv, is_compression)
        mode = "key-armed demo" if ROCKETRIDE_API_KEY else "offline demo"
        self.log_event(
            f"[RocketRide] {mode} classified energy state as {energy.upper()} "
            f"with {ROCKETRIDE_MODEL} policy."
        )
        return energy

    def fetch_task_by_complexity(self, complexity):
        task_title = "No compatible tasks found"
        try:
            with GraphDatabase.driver(URI, auth=AUTH) as driver:
                with driver.session() as session:
                    self.log_event(f"[Neo4j] Selecting {complexity} task with blocker traversal.")
                    # Traversal query: Only return a task if there is no uncompleted blocking task linked to it
                    query = """
                    MATCH (t:Task)
                    WHERE t.complexity = $complexity
                    AND NOT EXISTS {
                        MATCH (blocking:Task)-[:BLOCKS]->(t)
                        WHERE NOT blocking.status = "completed"
                    }
                    RETURN t.title AS title
                    LIMIT 1
                    """
                    result = session.run(query, complexity=complexity)
                    record = result.single()
                    if record:
                        task_title = record["title"]
                        self.log_event(f"[Neo4j] Selected unblocked task: {task_title}")
                    else:
                        blocked_query = """
                        MATCH (t:Task)
                        WHERE t.complexity = $complexity
                        OPTIONAL MATCH (blocking:Task)-[:BLOCKS]->(t)
                        WHERE blocking.status IS NULL OR blocking.status <> "completed"
                        WITH t, collect(blocking.title) AS blockers
                        RETURN t.title AS title, blockers
                        ORDER BY size(blockers) DESC, title ASC
                        LIMIT 3
                        """
                        blocked_result = list(session.run(blocked_query, complexity=complexity))
                        blocked_candidates = [
                            {
                                "title": row["title"],
                                "blockers": [b for b in row["blockers"] if b],
                            }
                            for row in blocked_result
                        ]
                        if blocked_candidates:
                            for candidate in blocked_candidates:
                                blockers = ", ".join(candidate["blockers"])
                                if blockers:
                                    self.log_event(
                                        "[Neo4j] Blocked candidate: "
                                        f"{candidate['title']} waits on {blockers}."
                                    )
                                else:
                                    self.log_event(
                                        "[Neo4j] Candidate had no blockers but was not selected: "
                                        f"{candidate['title']}."
                                    )

                            first_blocked = next(
                                (
                                    candidate
                                    for candidate in blocked_candidates
                                    if candidate["blockers"]
                                ),
                                None,
                            )
                            if first_blocked:
                                blocker_text = ", ".join(first_blocked["blockers"][:2])
                                task_title = (
                                    f"Blocked: {first_blocked['title']} <- {blocker_text}"
                                )
                        else:
                            self.log_event(
                                f"[Neo4j] No {complexity} tasks exist in the graph."
                            )
        except Exception as e:
            self.log_event(f"[DB Error] Database query failed: {e}", stderr=True)
        return task_title

    def parse_numeric_value(self, raw_string):
        if not raw_string:
            return 0.0
        # Extracts numbers and decimals from string (e.g., "112 mg/dL" -> 112.0)
        try:
            cleaned = "".join([c for c in str(raw_string) if c.isdigit() or c == "." or c == "-"])
            return float(cleaned) if cleaned else 0.0
        except Exception:
            return 0.0

    def get_live_biometrics(self):
        glucose_change = 0.0
        hrv = 55.0
        is_compression = False

        if not self.butterbase_enabled:
            return self.demo_biometrics()

        try:
            import requests

            headers = {
                "Authorization": f"Bearer {BUTTERBASE_API_TOKEN}"
            }
            # Query the auto-generated REST endpoint directly over HTTPS
            url = f"{BUTTERBASE_API_BASE}/wearable_logs"
            self.log_event("[Butterbase] Pulling latest wearable_logs snapshot.")
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                records = response.json() # Returns a list of JSON dictionary rows
                self.log_event(f"[Butterbase] Retrieved {len(records)} wearable rows.")

                # Sort records dynamically by ISO timestamp in descending order
                records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

                if len(records) >= 1:
                    latest_glucose = self.parse_numeric_value(records[0].get("glucose", "0"))
                    hrv = self.parse_numeric_value(records[0].get("hrv", "55"))
                    is_compression = records[0].get("is_compression_low", False)

                    # Calculate rate-of-change (dG/dt) if we have a previous baseline row
                    if len(records) >= 2:
                        previous_glucose = self.parse_numeric_value(records[1].get("glucose", "0"))
                        glucose_change = latest_glucose - previous_glucose
                    self.log_event(
                        "[Biometrics] "
                        f"dG/dt={glucose_change:.1f}, HRV={hrv:.1f}, "
                        f"compression_low={is_compression}."
                    )
            else:
                if response.status_code == 404:
                    self.butterbase_enabled = False
                    self.warn_butterbase_unavailable(
                        "[API Error] Butterbase app/table was not found. "
                        "Set BUTTERBASE_APP_ID and BUTTERBASE_API_TOKEN in "
                        "projects/vagus-graph/.env; using demo biometrics."
                    )
                    return self.demo_biometrics()

                self.warn_butterbase_unavailable(
                    "[API Error] Butterbase returned status "
                    f"{response.status_code}: {response.text}; using demo biometrics."
                )
                return self.demo_biometrics()

        except Exception as e:
            self.warn_butterbase_unavailable(
                "[Network Error] Failed to fetch biometrics from Auto-API: "
                f"{e}; using demo biometrics."
            )
            return self.demo_biometrics()

        return glucose_change, hrv, is_compression

    def update_menu_tasks(self):
        for item in list(self.menu.keys()):
            if item != "Refresh Tasks":
                del self.menu[item]

        # Classify and query task complexity based on physical inputs
        glucose_change, hrv, is_compression = self.get_live_biometrics()

        energy_level = self.run_rocketride_classification(
            glucose_change,
            hrv,
            is_compression,
        )
        self.log_event(
            f"[Classifier] RocketRide evaluated energy as {energy_level.upper()}."
        )

        recommended_task = self.fetch_task_by_complexity(energy_level)

        self.menu.add(f"Energy State: {energy_level.upper()}")
        self.menu.add(f"Recommended Task: {recommended_task}")
        return energy_level

    # Standard python bound method signature
    def run_biometric_loop(self, sender):
        # Update metrics and retrieve the evaluated state
        energy = self.update_menu_tasks()

        if energy == "high":
            self.title = "🔋 Vagus: OPTIMAL"
        elif energy == "medium":
            self.title = "⚡ Vagus: WARNING"
        else:
            self.title = "🚨 Vagus: CRASH"
            self.log_event("[Alert] CRASH detected! Spawning programmatic Daytona sandbox via SDK...")

            try:
                from daytona import Daytona, DaytonaConfig

                daytona_client = Daytona(DaytonaConfig())
                # Spawns sandbox container via native SDK
                sandbox = daytona_client.create()
                self.log_event(f"[Daytona] Sandbox created with ID: {sandbox.id}")

                # Execute automated verification checks securely inside the container
                response = sandbox.process.code_run("print('Daytona SDK execution verified.')")

                if response.exit_code != 0:
                    self.log_event(
                        f"[Daytona Error] Execution failed: {response.result}",
                        stderr=True,
                    )
                else:
                    self.log_event(f"[Daytona Output] {response.result.strip()}")

                # Teardown: Clean up the container immediately to free up account vCPU limit
                self.log_event("[Daytona] Tearing down sandbox...")
                sandbox.delete()
                self.log_event("[Daytona] Sandbox successfully destroyed. Concurrency limit protected.")

            except Exception as e:
                self.log_event(
                    f"[Daytona Error] Failed to execute sandbox workflow: {e}",
                    stderr=True,
                )

    @rumps.clicked("Refresh Tasks")
    def on_refresh(self, _):
        self.log_event("[UI] Manual refresh triggered by user.")
        self.update_menu_tasks()

if __name__ == "__main__":
    try:
        app = VagusMenuBarApp()
        app.run()
    except Exception as err:
        print(f"[Fatal] Application crashed on startup: {err}", file=sys.stderr)
