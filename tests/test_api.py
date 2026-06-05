"""Smoke tests for the FastAPI server. Mock runs only — zero LLM cost."""
from __future__ import annotations

import json
import time
import unittest

try:
    from fastapi.testclient import TestClient

    from cv_critic_agent.api import app

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi not installed (install with `pip install -e '.[server]'`)")
class ApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_graph_topology(self) -> None:
        response = self.client.get("/api/graph")
        self.assertEqual(response.status_code, 200)
        agents = response.json()["agents"]
        self.assertEqual({a["id"] for a in agents}, {"global_critic", "printable_cv_critic", "strategy_agent"})
        strategy = next(a for a in agents if a["id"] == "strategy_agent")
        self.assertEqual(set(strategy["depends_on"]), {"global_critic", "printable_cv_critic"})

    def test_sources_listing(self) -> None:
        response = self.client.get("/api/sources")
        self.assertEqual(response.status_code, 200)
        names = {s["name"] for s in response.json()["sources"]}
        self.assertIn("data.ts", names)

    def test_source_path_traversal_rejected(self) -> None:
        for bad in ["../etc/passwd", "..%2Fetc%2Fpasswd", ".env", "subdir/file"]:
            response = self.client.get(f"/api/sources/{bad}")
            self.assertIn(response.status_code, (400, 404))

    def test_run_lifecycle_mock(self) -> None:
        # 1. Create a mock run.
        create = self.client.post("/api/runs", json={"mock": True})
        self.assertEqual(create.status_code, 200)
        run_id = create.json()["run_id"]
        self.assertTrue(run_id)

        # 2. Poll until the run finishes.
        for _ in range(20):
            time.sleep(0.1)
            snapshot = self.client.get(f"/api/runs/{run_id}").json()
            if snapshot["status"] != "running":
                break
        self.assertEqual(snapshot["status"], "done")

        # 3. Event log should contain the lifecycle markers.
        event_types = {e["type"] for e in snapshot["events"]}
        for required in ("run_started", "agent_started", "agent_completed", "file_written", "run_completed"):
            self.assertIn(required, event_types)

        # 4. Reports must be readable.
        for slug in ("global", "printable-cv", "strategy"):
            response = self.client.get(f"/api/runs/{run_id}/reports/{slug}")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.text.strip())

    def test_real_run_requires_token(self) -> None:
        # CV_CRITIC_API_TOKEN is not set in test env → real runs must 503.
        response = self.client.post("/api/runs", json={"mock": False})
        self.assertEqual(response.status_code, 503)

    def test_sse_stream_replays_then_terminates(self) -> None:
        create = self.client.post("/api/runs", json={"mock": True})
        run_id = create.json()["run_id"]

        # Give the worker a moment to publish events.
        time.sleep(0.5)
        with self.client.stream("GET", f"/api/runs/{run_id}/events") as response:
            self.assertEqual(response.status_code, 200)
            events_seen = []
            for line in response.iter_lines():
                if not line or line.startswith(":"):
                    continue
                if line.startswith("data: "):
                    events_seen.append(json.loads(line[6:]))
                    if events_seen[-1]["type"] in ("run_completed", "run_failed"):
                        break

        types = {e["type"] for e in events_seen}
        self.assertIn("run_started", types)
        self.assertIn("run_completed", types)


if __name__ == "__main__":
    unittest.main()
