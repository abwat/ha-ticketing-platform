import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


class TicketApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {
                "TICKETING_DB": f"{self.tmpdir.name}/ticketing.sqlite",
                "DATABASE_URL": "",
                "REDIS_URL": "",
            },
        )
        self.env.start()
        from ticketing.main import build_app

        self.client = TestClient(build_app())

    def tearDown(self) -> None:
        self.client.close()
        self.env.stop()
        self.tmpdir.cleanup()

    def test_ticket_workflow_exposes_expected_status_codes(self) -> None:
        created = self.client.post(
            "/tickets",
            json={
                "title": "VPN down",
                "description": "Office users cannot connect",
                "priority": "critical",
                "requester": "ops@example.com",
            },
        )
        self.assertEqual(created.status_code, 201)
        ticket_id = created.json()["id"]

        assigned = self.client.post(
            f"/tickets/{ticket_id}/assign",
            json={"assignee": "alice"},
        )
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.json()["status"], "assigned")

        invalid_transition = self.client.post(
            f"/tickets/{ticket_id}/transition",
            json={"status": "closed"},
        )
        self.assertEqual(invalid_transition.status_code, 409)

        comment = self.client.post(
            f"/tickets/{ticket_id}/comments",
            json={"author": "alice", "body": "Checking gateway logs."},
        )
        self.assertEqual(comment.status_code, 201)

        comments = self.client.get(f"/tickets/{ticket_id}/comments")
        self.assertEqual(comments.status_code, 200)
        self.assertEqual(comments.json()[0]["body"], "Checking gateway logs.")

    def test_readiness_and_metrics_reflect_runtime_state(self) -> None:
        ready = self.client.get("/ready")
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["status"], "ready")

        self.client.post(
            "/tickets",
            json={"title": "Laptop issue", "priority": "low", "requester": "sam"},
        )
        metrics = self.client.get("/metrics")
        self.assertEqual(metrics.status_code, 200)
        self.assertIn('ticketing_tickets_total{status="open"} 1', metrics.text)
        self.assertIn("ticketing_pending_events 1", metrics.text)


if __name__ == "__main__":
    unittest.main()
