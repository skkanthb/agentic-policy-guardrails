import unittest
from fastapi.testclient import TestClient
from src.proxy_server import app

class TestACCPProxy(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_under_threshold_allowed(self):
        payload = {"account": "ACC-88219", "new_limit": 30000}
        response = self.client.post("/api/v1/credit", json=payload)
        # Should pass policy check (not blocked)
        self.assertNotEqual(response.status_code, 403)

    def test_over_threshold_blocked(self):
        payload = {"account": "ACC-88219", "new_limit": 85000}
        response = self.client.post("/api/v1/credit", json=payload)
        # Should be blocked by proxy
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error_code"], "POLICY_BREACH_HITL_REQUIRED")

if __name__ == "__main__":
    unittest.main()
