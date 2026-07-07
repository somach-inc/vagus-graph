"""Local telemetry capture and sensor fusion for Vagus Graph."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree

try:
    import requests
except ImportError:  # pragma: no cover - fallback is for minimal Python installs.
    requests = None  # type: ignore[assignment]


BUTTERBASE_WEARABLE_LOGS_URL = "https://api.butterbase.ai/v1/db/wearable_logs"
OURA_API_BASE_URL = "https://api.ouraring.com/v2/usercollection"
APPLE_HEALTH_BLOOD_GLUCOSE_TYPE = "HKQuantityTypeIdentifierBloodGlucose"
MMOL_L_TO_MG_DL = 18.0182


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
    def get(
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: float = 10.0,
    ) -> _UrllibResponse:
        query = f"?{urlencode(params)}" if params else ""
        http_request = urllib_request.Request(
            f"{url}{query}",
            headers=headers or {},
            method="GET",
        )
        try:
            with urllib_request.urlopen(http_request, timeout=timeout) as response:
                return _UrllibResponse(response.status, response.read())
        except HTTPError as exc:
            return _UrllibResponse(exc.code, exc.read())
        except URLError as exc:
            raise TelemetryError("HTTP request failed.") from exc

    @staticmethod
    def post(
        url: str,
        json: dict[str, object],
        timeout: float,
        headers: dict[str, str] | None = None,
    ) -> _UrllibResponse:
        body = json_module_dumps(json)
        http_request = urllib_request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", **(headers or {})},
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


@dataclass(frozen=True, slots=True)
class AppleHealthGlucoseReading:
    """Blood glucose record parsed from an Apple Health export."""

    glucose_mg_dl: float
    observed_at: datetime


class VagusSensorEngine:
    """Poll configured sensors, filter known CGM artifacts, and post telemetry."""

    def __init__(
        self,
        butterbase_url: str = BUTTERBASE_WEARABLE_LOGS_URL,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.butterbase_url = butterbase_url
        self.timeout_seconds = timeout_seconds

    def poll_dexcom_share_follow(self) -> dict[str, Any]:
        """Return Stelo glucose from Apple Health export or mock Dexcom readings."""
        apple_health_export_path = os.environ.get("APPLE_HEALTH_EXPORT_XML")
        if apple_health_export_path:
            return self.poll_stelo_from_apple_health(Path(apple_health_export_path))

        return {
            "data": [
                {"glucose_mg_dl": 118.0, "timestamp": "2026-07-07T12:00:00Z"},
                {"glucose_mg_dl": 101.5, "timestamp": "2026-07-07T12:05:00Z"},
            ]
        }

    def poll_stelo_from_apple_health(self, export_xml_path: Path) -> dict[str, Any]:
        """Read the latest two Stelo glucose values from Apple Health export XML."""
        readings = self.read_apple_health_glucose_readings(export_xml_path)
        if len(readings) < 2:
            raise TelemetryError("Apple Health export requires at least two glucose readings.")

        latest_two = sorted(readings, key=lambda reading: reading.observed_at)[-2:]
        return {
            "data": [
                {
                    "glucose_mg_dl": reading.glucose_mg_dl,
                    "timestamp": reading.observed_at.isoformat(),
                }
                for reading in latest_two
            ]
        }

    @staticmethod
    def read_apple_health_glucose_readings(
        export_xml_path: Path,
    ) -> list[AppleHealthGlucoseReading]:
        """Parse Apple Health blood glucose records from export.xml."""
        if not export_xml_path.exists():
            raise TelemetryError(f"Apple Health export not found: {export_xml_path}")

        readings: list[AppleHealthGlucoseReading] = []
        try:
            for _, element in ElementTree.iterparse(export_xml_path, events=("end",)):
                if element.tag != "Record":
                    element.clear()
                    continue
                if element.attrib.get("type") != APPLE_HEALTH_BLOOD_GLUCOSE_TYPE:
                    element.clear()
                    continue

                value = float(element.attrib["value"])
                unit = element.attrib.get("unit", "mg/dL")
                glucose_mg_dl = (
                    value * MMOL_L_TO_MG_DL
                    if unit.lower() in {"mmol/l", "mmol/litre", "mmol/liter"}
                    else value
                )
                timestamp = element.attrib.get("endDate") or element.attrib["startDate"]
                readings.append(
                    AppleHealthGlucoseReading(
                        glucose_mg_dl=glucose_mg_dl,
                        observed_at=VagusSensorEngine.parse_apple_health_datetime(timestamp),
                    )
                )
                element.clear()
        except (ElementTree.ParseError, KeyError, TypeError, ValueError) as exc:
            raise TelemetryError("Failed to parse Apple Health glucose export.") from exc

        return readings

    @staticmethod
    def parse_apple_health_datetime(value: str) -> datetime:
        """Parse Apple Health timestamps into timezone-aware datetimes."""
        for date_format in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                continue
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

    def poll_oura_ring(self) -> dict[str, Any]:
        """Return real Oura Cloud data when configured, otherwise mock telemetry."""
        if os.environ.get("OURA_ACCESS_TOKEN"):
            return self.poll_oura_cloud()

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

    def poll_oura_cloud(self) -> dict[str, Any]:
        """Poll Oura Cloud API for HRV and activity-derived motion state."""
        end_date = date.today()
        start_date = end_date - timedelta(days=2)
        activity_payload = self.get_oura_endpoint(
            "daily_activity",
            {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        )
        sleep_payload = self.get_oura_endpoint(
            "daily_sleep",
            {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        )

        activity_data = activity_payload.get("data", [])
        sleep_data = sleep_payload.get("data", [])
        if not isinstance(activity_data, list) or not isinstance(sleep_data, list):
            raise TelemetryError("Oura API payload data fields must be lists.")

        latest_activity = activity_data[-1] if activity_data else {}
        if not isinstance(latest_activity, dict):
            latest_activity = {}
        steps = int(float(latest_activity.get("steps", 0) or 0))
        met_minutes = float(latest_activity.get("met_minutes", 0.0) or 0.0)
        motion_detected = steps > 0 or met_minutes >= 2.0

        hrv_ms = self.extract_oura_hrv_ms(sleep_data)
        is_vertical = self.read_bool_env("OURA_IS_VERTICAL", default=motion_detected)
        return {
            "heartrate": {
                "data": [
                    {
                        "bpm": int(float(latest_activity.get("average_met_minutes", 72) or 72)),
                        "hrv_ms": hrv_ms,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                ]
            },
            "daily_activity": {"data": [{"steps": steps, "met_minutes": met_minutes}]},
            "posture": {
                "motion_detected": motion_detected,
                "is_vertical": is_vertical,
            },
        }

    def get_oura_endpoint(
        self,
        endpoint: str,
        params: dict[str, str],
    ) -> dict[str, Any]:
        """Call an Oura Cloud API endpoint using the configured access token."""
        access_token = os.environ.get("OURA_ACCESS_TOKEN")
        if not access_token:
            raise TelemetryError("OURA_ACCESS_TOKEN is required for Oura Cloud polling.")

        try:
            response = requests.get(
                f"{OURA_API_BASE_URL}/{endpoint}",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise TelemetryError(f"Failed to poll Oura endpoint: {endpoint}") from exc

        if not isinstance(payload, dict):
            raise TelemetryError(f"Oura endpoint returned non-object JSON: {endpoint}")
        return payload

    @staticmethod
    def extract_oura_hrv_ms(sleep_data: list[object]) -> int:
        """Extract average HRV from Oura daily sleep payload variants."""
        for item in reversed(sleep_data):
            if not isinstance(item, dict):
                continue
            for key in ("average_hrv", "avg_hrv", "hrv_ms"):
                value = item.get(key)
                if isinstance(value, int | float):
                    return int(round(float(value)))

            contributors = item.get("contributors")
            if isinstance(contributors, dict):
                value = contributors.get("hrv_balance")
                if isinstance(value, int | float):
                    return int(round(float(value)))

            hrv = item.get("hrv")
            if isinstance(hrv, dict):
                for key in ("average", "avg", "value"):
                    value = hrv.get(key)
                    if isinstance(value, int | float):
                        return int(round(float(value)))

        return 32

    @staticmethod
    def read_bool_env(key: str, default: bool) -> bool:
        """Read a boolean environment variable."""
        value = os.environ.get(key)
        if value is None or value == "":
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

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
