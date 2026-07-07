"""Local telemetry capture and sensor fusion for Vagus Graph."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

try:
    import requests
except ImportError:  # pragma: no cover - fallback is for minimal Python installs.
    requests = None  # type: ignore[assignment]


BUTTERBASE_WEARABLE_LOGS_URL = "https://api.butterbase.ai/v1/db/wearable_logs"


class TelemetryError(RuntimeError):
    """Raised when telemetry capture or submission fails."""


class _UrllibResponse:
    """Small response adapter used when the requests package is unavailable."""

    def __init__(self, status_code: int, body: bytes) -> None:
        self.status_code = status_code
        self.body = body

    def raise_for_status(self) -> None:
        """Raise for non-2xx HTTP statuses."""
        if self.status_code < 200 or self.status_code >= 300:
            raise TelemetryError(f"HTTP request failed with status {self.status_code}.")


class _HttpClient:
    """Requests-compatible subset backed by urllib."""

    @staticmethod
    def post(
        url: str,
        json: dict[str, object],
        timeout: float,
    ) -> _UrllibResponse:
        body = json_module_dumps(json)
        http_request = urllib_request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(http_request, timeout=timeout) as response:
                return _UrllibResponse(response.status, response.read())
        except HTTPError as exc:
            return _UrllibResponse(exc.code, exc.read())
        except URLError as exc:
            raise TelemetryError("HTTP request failed.") from exc


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


@dataclass(frozen=True, slots=True)
class TelemetryReading:
    """Cleaned telemetry record used by the cognitive pipeline."""

    glucose_rate_of_change: float
    hrv_ms: int
    motion_detected: bool
    is_vertical: bool
    is_compression_low: bool

    def as_dict(self) -> dict[str, object]:
        """Return a serializable telemetry dictionary."""
        return {
            "glucose_rate_of_change": self.glucose_rate_of_change,
            "hrv_ms": self.hrv_ms,
            "motion_detected": self.motion_detected,
            "is_vertical": self.is_vertical,
            "is_compression_low": self.is_compression_low,
        }


class VagusSensorEngine:
    """Poll mock sensor APIs, filter known CGM artifacts, and post telemetry."""

    def __init__(
        self,
        butterbase_url: str = BUTTERBASE_WEARABLE_LOGS_URL,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.butterbase_url = butterbase_url
        self.timeout_seconds = timeout_seconds

    def poll_dexcom_share_follow(self) -> dict[str, Any]:
        """Return a mock Dexcom Share Follow response with two 5-minute readings."""
        return {
            "data": [
                {"glucose_mg_dl": 118.0, "timestamp": "2026-07-07T12:00:00Z"},
                {"glucose_mg_dl": 101.5, "timestamp": "2026-07-07T12:05:00Z"},
            ]
        }

    def poll_oura_ring(self) -> dict[str, Any]:
        """Return a mock Oura response shaped like relevant wearable telemetry."""
        return {
            "heartrate": {
                "data": [
                    {
                        "bpm": 72,
                        "hrv_ms": 32,
                        "timestamp": "2026-07-07T12:05:00Z",
                    }
                ]
            },
            "daily_activity": {"data": [{"steps": 0, "met_minutes": 0.5}]},
            "posture": {"motion_detected": False, "is_vertical": False},
        }

    @staticmethod
    def calculate_glucose_rate_of_change(
        previous_glucose_mg_dl: float,
        current_glucose_mg_dl: float,
    ) -> float:
        """Calculate glucose change across the 5-minute Dexcom polling interval."""
        return current_glucose_mg_dl - previous_glucose_mg_dl

    @staticmethod
    def is_compression_low(
        glucose_rate_of_change: float,
        motion_detected: bool,
        is_vertical: bool,
    ) -> bool:
        """Detect likely compression lows caused by horizontal immobility."""
        return (
            glucose_rate_of_change < -15.0
            and motion_detected is False
            and is_vertical is False
        )

    def collect_clean_telemetry(self) -> dict[str, object]:
        """Collect mock sensor data and return the cleaned telemetry payload."""
        try:
            dexcom_payload = self.poll_dexcom_share_follow()
            oura_payload = self.poll_oura_ring()

            glucose_points = dexcom_payload["data"]
            if len(glucose_points) < 2:
                raise TelemetryError("Dexcom payload requires at least two readings.")

            previous_glucose = float(glucose_points[-2]["glucose_mg_dl"])
            current_glucose = float(glucose_points[-1]["glucose_mg_dl"])
            glucose_rate_of_change = self.calculate_glucose_rate_of_change(
                previous_glucose,
                current_glucose,
            )

            heart_rate_points = oura_payload["heartrate"]["data"]
            if not heart_rate_points:
                raise TelemetryError("Oura heart rate payload contains no readings.")

            hrv_ms = int(heart_rate_points[-1]["hrv_ms"])
            posture = oura_payload["posture"]
            motion_detected = bool(posture["motion_detected"])
            is_vertical = bool(posture["is_vertical"])

            reading = TelemetryReading(
                glucose_rate_of_change=glucose_rate_of_change,
                hrv_ms=hrv_ms,
                motion_detected=motion_detected,
                is_vertical=is_vertical,
                is_compression_low=self.is_compression_low(
                    glucose_rate_of_change,
                    motion_detected,
                    is_vertical,
                ),
            )
            return reading.as_dict()
        except (KeyError, TypeError, ValueError) as exc:
            raise TelemetryError("Failed to parse sensor telemetry payloads.") from exc

    def post_clean_telemetry(self, telemetry: dict[str, object]) -> None:
        """Post cleaned telemetry to the Butterbase wearable logs endpoint."""
        headers = {}
        butterbase_api_key = os.environ.get("BUTTERBASE_API_KEY")
        if butterbase_api_key:
            headers["Authorization"] = f"Bearer {butterbase_api_key}"

        try:
            if headers:
                response = requests.post(
                    self.butterbase_url,
                    headers=headers,
                    json=telemetry,
                    timeout=self.timeout_seconds,
                )
            else:
                response = requests.post(
                    self.butterbase_url,
                    json=telemetry,
                    timeout=self.timeout_seconds,
                )
            response.raise_for_status()
        except Exception as exc:
            raise TelemetryError("Failed to post telemetry to Butterbase.") from exc

    def run_once(self) -> dict[str, object]:
        """Collect, filter, submit, and return one telemetry reading."""
        telemetry = self.collect_clean_telemetry()
        self.post_clean_telemetry(telemetry)
        return telemetry


def main() -> None:
    """Run one local telemetry capture cycle."""
    engine = VagusSensorEngine()
    engine.run_once()


if __name__ == "__main__":
    main()
