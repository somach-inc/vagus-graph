"""Native macOS menu bar application for Vagus Graph."""

from __future__ import annotations

import os
import json
import subprocess
import threading
import time
from typing import Any, Protocol, cast
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

try:
    import requests
except ImportError:  # pragma: no cover - fallback is for minimal Python installs.
    requests = None  # type: ignore[assignment]

try:
    import rumps
except ImportError:  # pragma: no cover - exercised by import safety, not app runtime.
    rumps = None  # type: ignore[assignment]


BUTTERBASE_WEARABLE_LOGS_URL = "https://api.butterbase.ai/v1/db/wearable_logs"
ROCKETRIDE_PIPELINE_URL = (
    "https://api.rocketride.cloud/v1/pipelines/vagus_cognitive_pipeline/run"
)
DAYTONA_COMMAND = [
    "daytona",
    "create",
    "bci-build-sandbox",
    "--template",
    "python",
    "--code",
    "https://github.com/CarlKho-Minerva/bci-core-repo",
]
POLL_INTERVAL_SECONDS = 300.0


class AppRuntimeError(RuntimeError):
    """Raised when the menu bar pipeline cannot complete an operation."""


class _UrllibResponse:
    """Small response adapter used when the requests package is unavailable."""

    def __init__(self, status_code: int, body: bytes) -> None:
        self.status_code = status_code
        self.body = body

    def raise_for_status(self) -> None:
        """Raise for non-2xx HTTP statuses."""
        if self.status_code < 200 or self.status_code >= 300:
            raise AppRuntimeError(f"HTTP request failed with status {self.status_code}.")

    def json(self) -> object:
        """Decode response JSON."""
        return json.loads(self.body.decode("utf-8"))


class _HttpClient:
    """Requests-compatible subset backed by urllib."""

    @staticmethod
    def get(url: str, timeout: float) -> _UrllibResponse:
        http_request = urllib_request.Request(url, method="GET")
        return _HttpClient._open(http_request, timeout)

    @staticmethod
    def post(
        url: str,
        headers: dict[str, str],
        json: dict[str, object],
        timeout: float,
    ) -> _UrllibResponse:
        body = json_module_dumps(json)
        request_headers = {"Content-Type": "application/json", **headers}
        http_request = urllib_request.Request(
            url,
            data=body,
            headers=request_headers,
            method="POST",
        )
        return _HttpClient._open(http_request, timeout)

    @staticmethod
    def _open(
        http_request: urllib_request.Request,
        timeout: float,
    ) -> _UrllibResponse:
        try:
            with urllib_request.urlopen(http_request, timeout=timeout) as response:
                return _UrllibResponse(response.status, response.read())
        except HTTPError as exc:
            return _UrllibResponse(exc.code, exc.read())
        except URLError as exc:
            raise AppRuntimeError("HTTP request failed.") from exc


def json_module_dumps(payload: dict[str, object]) -> bytes:
    """Serialize JSON payloads for the urllib fallback."""
    return json.dumps(payload).encode("utf-8")


if requests is None:
    requests = _HttpClient()  # type: ignore[assignment]


def load_dotenv_if_available() -> None:
    """Load local .env values when python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


load_dotenv_if_available()


class MenuAppProtocol(Protocol):
    """Small protocol for objects with mutable menu titles."""

    title: str


if rumps is None:

    class _BaseApp:
        def __init__(self, name: str) -> None:
            self.name = name
            self.title = name

        def run(self) -> None:
            raise AppRuntimeError("rumps is required to run the macOS menu app.")

else:
    _BaseApp = rumps.App


class VagusMenuBarApp(_BaseApp):
    """Poll RocketRide and route cognitive state to macOS menu bar actions."""

    def __init__(
        self,
        butterbase_url: str = BUTTERBASE_WEARABLE_LOGS_URL,
        rocketride_url: str = ROCKETRIDE_PIPELINE_URL,
        poll_interval_seconds: float = POLL_INTERVAL_SECONDS,
        start_background_thread: bool = True,
    ) -> None:
        super().__init__("Vagus Graph")
        self.butterbase_url = butterbase_url
        self.rocketride_url = rocketride_url
        self.poll_interval_seconds = poll_interval_seconds
        self.timeout_seconds = 10.0
        self._stop_event = threading.Event()
        if start_background_thread:
            thread = threading.Thread(target=self.poll_forever, daemon=True)
            thread.start()

    def fetch_latest_telemetry(self) -> dict[str, object]:
        """Fetch the latest telemetry dictionary from Butterbase wearable logs."""
        headers = {}
        butterbase_api_key = os.environ.get("BUTTERBASE_API_KEY")
        if butterbase_api_key:
            headers["Authorization"] = f"Bearer {butterbase_api_key}"

        try:
            if headers:
                response = requests.get(
                    self.butterbase_url,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
            else:
                response = requests.get(
                    self.butterbase_url,
                    timeout=self.timeout_seconds,
                )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise AppRuntimeError("Failed to fetch latest Butterbase telemetry.") from exc
        except ValueError as exc:
            raise AppRuntimeError("Butterbase returned invalid JSON.") from exc

        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            latest = payload["data"][0] if payload["data"] else None
        else:
            latest = payload

        if not isinstance(latest, dict):
            raise AppRuntimeError("Butterbase response did not contain telemetry.")

        return cast(dict[str, object], latest)

    @staticmethod
    def build_rocketride_payload(telemetry: dict[str, object]) -> dict[str, object]:
        """Build the RocketRide input envelope from Butterbase telemetry."""
        return {
            "input": {
                "glucose_rate_of_change": telemetry["glucose_rate_of_change"],
                "hrv_ms": telemetry["hrv_ms"],
                "is_compression_low": telemetry["is_compression_low"],
            }
        }

    def run_pipeline(self, telemetry: dict[str, object]) -> dict[str, object]:
        """Submit telemetry to RocketRide and return its JSON payload."""
        headers = {}
        token = os.environ.get("ROCKETRIDE_SECRET")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = requests.post(
                self.rocketride_url,
                headers=headers,
                json=self.build_rocketride_payload(telemetry),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise AppRuntimeError("Failed to run RocketRide pipeline.") from exc
        except (KeyError, ValueError) as exc:
            raise AppRuntimeError("RocketRide returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise AppRuntimeError("RocketRide response must be a JSON object.")
        return cast(dict[str, object], payload)

    @staticmethod
    def parse_pipeline_response(payload: dict[str, object]) -> tuple[str, str]:
        """Extract classified state and recommended task from RocketRide output."""
        try:
            output = payload["output"]
            if not isinstance(output, dict):
                raise TypeError("output must be an object")
            query_results = output["neo4j_aura_query"]
            if not isinstance(query_results, list) or not query_results:
                raise TypeError("neo4j_aura_query must be a non-empty list")
            first_result = query_results[0]
            if not isinstance(first_result, dict):
                raise TypeError("query result must be an object")
            classified_state = first_result["classified_state"]
            recommended_task = first_result["recommended_task"]
            if not isinstance(classified_state, str) or not isinstance(
                recommended_task,
                str,
            ):
                raise TypeError("state and task must be strings")
            return classified_state, recommended_task
        except (KeyError, TypeError) as exc:
            raise AppRuntimeError("RocketRide response schema is invalid.") from exc

    def update_from_pipeline_response(self, payload: dict[str, object]) -> None:
        """Update the menu bar title and side effects from a pipeline payload."""
        classified_state, task_title = self.parse_pipeline_response(payload)

        if classified_state == "low":
            self.title = "⚠️ CRASH: Take Action"
            self.notify(
                "Vagus Graph",
                f"PFC energy low. Pivot to: {task_title}",
            )
            self.run_daytona_sandbox()
            return

        if classified_state == "medium":
            self.title = "⚡ MODERATE: Focus Routine"
            return

        if classified_state == "high":
            self.title = "🔋 OPTIMAL: Deep Work"
            return

        raise AppRuntimeError(f"Unknown cognitive state: {classified_state}")

    def notify(self, title: str, message: str) -> None:
        """Send a macOS notification when rumps is installed."""
        if rumps is None:
            return
        rumps.notification(title=title, subtitle="", message=message)

    def run_daytona_sandbox(self) -> subprocess.Popen[str]:
        """Spawn the Daytona development sandbox for low-energy recovery."""
        try:
            return subprocess.Popen(
                DAYTONA_COMMAND,
                text=True,
            )
        except OSError as exc:
            raise AppRuntimeError("Failed to start Daytona sandbox.") from exc

    def poll_once(self) -> None:
        """Run one Butterbase-to-RocketRide polling cycle."""
        telemetry = self.fetch_latest_telemetry()
        response = self.run_pipeline(telemetry)
        self.update_from_pipeline_response(response)

    def poll_forever(self) -> None:
        """Poll the RocketRide pipeline until the app shuts down."""
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except AppRuntimeError:
                self.title = "Vagus Graph: Sync issue"
            self._stop_event.wait(self.poll_interval_seconds)

    def stop_polling(self) -> None:
        """Stop the background polling loop."""
        self._stop_event.set()


def main() -> None:
    """Start the native menu bar application."""
    app = VagusMenuBarApp()
    app.run()


if __name__ == "__main__":
    main()
