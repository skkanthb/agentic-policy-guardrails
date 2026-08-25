import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.proxy_server import app

class TestACCPProxy(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("src.proxy_server.requests.post")
    def test_under_threshold_allowed(self, mock_post):
        # Mock OPA response for allowed request
        mock_post.side_effect = [
            unittest.mock.Mock(json=lambda: {"result": {"allow": True}}),
            unittest.mock.Mock(json=lambda: {"status": "SUCCESS"})
        ]
        payload = {"account": "ACC-88219", "new_limit": 30000}
        response = self.client.post("/api/v1/credit", json=payload)
        self.assertEqual(response.status_code, 200)

    @patch("src.proxy_server.requests.post")
    def test_over_threshold_blocked(self, mock_post):
        # Mock OPA response requiring HITL
        mock_post.return_value.json.return_value = {
            "result": {
                "requires_hitl": True,
                "deny_reason": "SOX Control Breach: Credit increase over $50,000 requires manager approval."
            }
        }
        payload = {"account": "ACC-88219", "new_limit": 85000}
        response = self.client.post("/api/v1/credit", json=payload)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error_code"], "POLICY_BREACH_HITL_REQUIRED")

if __name__ == "__main__":
    unittest.main()
