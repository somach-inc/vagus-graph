"""Unit tests for the Vagus Graph components."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

import app
from sensor_engine import TelemetryError, VagusSensorEngine


class SensorFusionTests(unittest.TestCase):
    """Verify compression-low filtering behavior."""

    def test_flags_compression_low_when_drop_static_and_horizontal(self) -> None:
        engine = VagusSensorEngine()

        result = engine.is_compression_low(
            glucose_rate_of_change=-16.5,
            motion_detected=False,
            is_vertical=False,
        )

        self.assertTrue(result)

    def test_does_not_flag_compression_low_when_vertical(self) -> None:
        engine = VagusSensorEngine()

        result = engine.is_compression_low(
            glucose_rate_of_change=-16.5,
            motion_detected=False,
            is_vertical=True,
        )

        self.assertFalse(result)

    def test_does_not_flag_compression_low_when_moving(self) -> None:
        engine = VagusSensorEngine()

        result = engine.is_compression_low(
            glucose_rate_of_change=-16.5,
            motion_detected=True,
            is_vertical=False,
        )

        self.assertFalse(result)

    def test_collect_clean_telemetry_from_mock_payloads(self) -> None:
        engine = VagusSensorEngine()

        with mock.patch.dict(
            "os.environ",
            {"APPLE_HEALTH_EXPORT_XML": "", "OURA_ACCESS_TOKEN": ""},
        ):
            telemetry = engine.collect_clean_telemetry()

        self.assertEqual(telemetry["glucose_rate_of_change"], -16.5)
        self.assertEqual(telemetry["hrv_ms"], 32)
        self.assertFalse(telemetry["motion_detected"])
        self.assertFalse(telemetry["is_vertical"])
        self.assertTrue(telemetry["is_compression_low"])

    @mock.patch("sensor_engine.requests.post")
    def test_posts_clean_telemetry_to_butterbase(
        self,
        mock_post: mock.Mock,
    ) -> None:
        response = mock.Mock()
        response.raise_for_status.return_value = None
        mock_post.return_value = response
        engine = VagusSensorEngine()
        with mock.patch.dict(
            "os.environ",
            {
                "APPLE_HEALTH_EXPORT_XML": "",
                "OURA_ACCESS_TOKEN": "",
                "BUTTERBASE_API_KEY": "",
            },
        ):
            telemetry = engine.collect_clean_telemetry()

            engine.post_clean_telemetry(telemetry)

        mock_post.assert_called_once_with(
            "https://api.butterbase.ai/v1/db/wearable_logs",
            json=telemetry,
            timeout=10.0,
        )

    def test_reads_stelo_glucose_from_apple_health_export(self) -> None:
        export_xml = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
  <Record type="HKQuantityTypeIdentifierBloodGlucose" sourceName="Stelo" unit="mg/dL" value="118" startDate="2026-07-07 12:00:00 -0700" endDate="2026-07-07 12:00:00 -0700"/>
  <Record type="HKQuantityTypeIdentifierBloodGlucose" sourceName="Stelo" unit="mg/dL" value="101" startDate="2026-07-07 12:05:00 -0700" endDate="2026-07-07 12:05:00 -0700"/>
</HealthData>
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "export.xml"
            export_path.write_text(export_xml, encoding="utf-8")
            engine = VagusSensorEngine()

            payload = engine.poll_stelo_from_apple_health(export_path)

        self.assertEqual(payload["data"][-2]["glucose_mg_dl"], 118.0)
        self.assertEqual(payload["data"][-1]["glucose_mg_dl"], 101.0)

    def test_collects_with_apple_health_export_when_configured(self) -> None:
        export_xml = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
  <Record type="HKQuantityTypeIdentifierBloodGlucose" unit="mg/dL" value="118" startDate="2026-07-07 12:00:00 -0700" endDate="2026-07-07 12:00:00 -0700"/>
  <Record type="HKQuantityTypeIdentifierBloodGlucose" unit="mg/dL" value="101" startDate="2026-07-07 12:05:00 -0700" endDate="2026-07-07 12:05:00 -0700"/>
</HealthData>
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "export.xml"
            export_path.write_text(export_xml, encoding="utf-8")
            engine = VagusSensorEngine()

            with mock.patch.dict(
                "os.environ",
                {
                    "APPLE_HEALTH_EXPORT_XML": str(export_path),
                    "OURA_ACCESS_TOKEN": "",
                },
            ):
                telemetry = engine.collect_clean_telemetry()

        self.assertEqual(telemetry["glucose_rate_of_change"], -17.0)
        self.assertTrue(telemetry["is_compression_low"])

    def test_apple_health_export_requires_two_glucose_readings(self) -> None:
        export_xml = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
  <Record type="HKQuantityTypeIdentifierBloodGlucose" unit="mg/dL" value="118" startDate="2026-07-07 12:00:00 -0700" endDate="2026-07-07 12:00:00 -0700"/>
</HealthData>
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "export.xml"
            export_path.write_text(export_xml, encoding="utf-8")
            engine = VagusSensorEngine()

            with self.assertRaises(TelemetryError):
                engine.poll_stelo_from_apple_health(export_path)

    @mock.patch("sensor_engine.requests.get")
    def test_polls_oura_cloud_when_access_token_is_configured(
        self,
        mock_get: mock.Mock,
    ) -> None:
        activity_response = mock.Mock()
        activity_response.raise_for_status.return_value = None
        activity_response.json.return_value = {
            "data": [{"steps": 0, "met_minutes": 0.5}]
        }
        sleep_response = mock.Mock()
        sleep_response.raise_for_status.return_value = None
        sleep_response.json.return_value = {"data": [{"average_hrv": 41}]}
        mock_get.side_effect = [activity_response, sleep_response]
        engine = VagusSensorEngine()

        with mock.patch.dict(
            "os.environ",
            {"OURA_ACCESS_TOKEN": "token", "OURA_IS_VERTICAL": "false"},
        ):
            payload = engine.poll_oura_ring()

        self.assertEqual(payload["heartrate"]["data"][0]["hrv_ms"], 41)
        self.assertFalse(payload["posture"]["motion_detected"])
        self.assertFalse(payload["posture"]["is_vertical"])


class MenuBarAppTests(unittest.TestCase):
    """Verify RocketRide state mapping to menu bar behavior."""

    def make_app(self) -> app.VagusMenuBarApp:
        return app.VagusMenuBarApp(start_background_thread=False)

    @staticmethod
    def pipeline_payload(state: str, task_title: str = "Task Title") -> dict[str, object]:
        return {
            "output": {
                "neo4j_aura_query": [
                    {
                        "recommended_task": task_title,
                        "classified_state": state,
                    }
                ]
            }
        }

    @mock.patch.object(app.VagusMenuBarApp, "run_daytona_sandbox")
    @mock.patch.object(app.VagusMenuBarApp, "notify")
    def test_low_state_updates_title_notifies_and_runs_daytona(
        self,
        mock_notify: mock.Mock,
        mock_daytona: mock.Mock,
    ) -> None:
        menu_app = self.make_app()

        menu_app.update_from_pipeline_response(
            self.pipeline_payload("low", "Upload sponsorship videos to drive"),
        )

        self.assertEqual(menu_app.title, "⚠️ CRASH: Take Action")
        mock_notify.assert_called_once_with(
            "Vagus Graph",
            "PFC energy low. Pivot to: Upload sponsorship videos to drive",
        )
        mock_daytona.assert_called_once_with()

    @mock.patch.object(app.VagusMenuBarApp, "run_daytona_sandbox")
    @mock.patch.object(app.VagusMenuBarApp, "notify")
    def test_medium_state_updates_title_only(
        self,
        mock_notify: mock.Mock,
        mock_daytona: mock.Mock,
    ) -> None:
        menu_app = self.make_app()

        menu_app.update_from_pipeline_response(self.pipeline_payload("medium"))

        self.assertEqual(menu_app.title, "⚡ MODERATE: Focus Routine")
        mock_notify.assert_not_called()
        mock_daytona.assert_not_called()

    @mock.patch.object(app.VagusMenuBarApp, "run_daytona_sandbox")
    @mock.patch.object(app.VagusMenuBarApp, "notify")
    def test_high_state_updates_title_only(
        self,
        mock_notify: mock.Mock,
        mock_daytona: mock.Mock,
    ) -> None:
        menu_app = self.make_app()

        menu_app.update_from_pipeline_response(self.pipeline_payload("high"))

        self.assertEqual(menu_app.title, "🔋 OPTIMAL: Deep Work")
        mock_notify.assert_not_called()
        mock_daytona.assert_not_called()

    @mock.patch("app.requests.post")
    @mock.patch("app.requests.get")
    def test_poll_once_fetches_butterbase_and_runs_rocketride(
        self,
        mock_get: mock.Mock,
        mock_post: mock.Mock,
    ) -> None:
        butterbase_response = mock.Mock()
        butterbase_response.raise_for_status.return_value = None
        butterbase_response.json.return_value = {
            "data": [
                {
                    "glucose_rate_of_change": -16.5,
                    "hrv_ms": 32,
                    "motion_detected": False,
                    "is_vertical": False,
                    "is_compression_low": True,
                }
            ]
        }
        rocketride_response = mock.Mock()
        rocketride_response.raise_for_status.return_value = None
        rocketride_response.json.return_value = self.pipeline_payload("medium")
        mock_get.return_value = butterbase_response
        mock_post.return_value = rocketride_response
        menu_app = self.make_app()

        with mock.patch.dict(
            "os.environ",
            {"BUTTERBASE_API_KEY": "", "ROCKETRIDE_SECRET": ""},
        ):
            menu_app.poll_once()

        self.assertEqual(menu_app.title, "⚡ MODERATE: Focus Routine")
        mock_get.assert_called_once_with(
            "https://api.butterbase.ai/v1/db/wearable_logs",
            timeout=10.0,
        )
        mock_post.assert_called_once_with(
            "https://api.rocketride.cloud/v1/pipelines/vagus_cognitive_pipeline/run",
            headers={},
            json={
                "input": {
                    "glucose_rate_of_change": -16.5,
                    "hrv_ms": 32,
                    "is_compression_low": True,
                }
            },
            timeout=10.0,
        )

    @mock.patch("app.subprocess.Popen")
    def test_run_daytona_sandbox_uses_expected_command(
        self,
        mock_popen: mock.Mock,
    ) -> None:
        process = mock.Mock()
        mock_popen.return_value = process
        menu_app = self.make_app()

        result = menu_app.run_daytona_sandbox()

        self.assertIs(result, process)
        mock_popen.assert_called_once_with(app.DAYTONA_COMMAND, text=True)


if __name__ == "__main__":
    unittest.main()
