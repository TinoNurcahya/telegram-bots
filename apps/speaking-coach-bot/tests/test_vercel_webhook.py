import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from api.index import app, settings


class TestVercelWebhookServerless(unittest.TestCase):
    """Test suite for Vercel FastAPI Serverless Webhook Adapter."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_check_endpoint(self):
        """Verify /health returns 200 OK with expected status info."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("service"), "SpeakingCoachBot")
        self.assertEqual(data.get("mode"), "vercel-serverless")

    def test_root_endpoint(self):
        """Verify root endpoint / returns online service metadata."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "online")
        self.assertEqual(data.get("runtime"), "Vercel Serverless")

    def test_webhook_secret_token_enforcement(self):
        """Verify unauthorized requests are rejected when webhook_secret is configured."""
        original_secret = settings.webhook_secret
        try:
            settings.webhook_secret = "super_secret_test_token_123"

            # 1. Missing secret header
            resp_missing = self.client.post("/api/index", json={"update_id": 100})
            self.assertEqual(resp_missing.status_code, 403)
            self.assertIn("invalid secret token", resp_missing.text)

            # 2. Invalid secret header
            resp_invalid = self.client.post(
                "/api/index",
                json={"update_id": 100},
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"},
            )
            self.assertEqual(resp_invalid.status_code, 403)

            # 3. Valid secret header
            with patch("api.index.dp.feed_update", new_callable=AsyncMock) as mock_feed:
                mock_feed.return_value = None
                resp_valid = self.client.post(
                    "/api/index",
                    json={"update_id": 101},
                    headers={"X-Telegram-Bot-Api-Secret-Token": "super_secret_test_token_123"},
                )
                self.assertEqual(resp_valid.status_code, 200)
                self.assertEqual(resp_valid.json(), {"ok": True})
                self.assertTrue(mock_feed.called)
        finally:
            settings.webhook_secret = original_secret

    def test_webhook_invalid_json(self):
        """Verify 400 Bad Request is returned on invalid JSON."""
        headers = {"Content-Type": "application/json"}
        if settings.webhook_secret:
            headers["X-Telegram-Bot-Api-Secret-Token"] = settings.webhook_secret
        response = self.client.post(
            "/api/index",
            content="not a json",
            headers=headers,
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
