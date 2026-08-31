import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.proxy_server import app

class TestACCPProxy(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("src.proxy_server.requests.post")
    def test_under_threshold_allowed(self, mock_post):
        mock_opa_resp = MagicMock()
        mock_opa_resp.json.return_value = {"result": {"allow": True, "require_hitl": False}}

        mock_sap_resp = MagicMock()
        mock_sap_resp.json.return_value = {"status": "SUCCESS"}

        mock_post.side_effect = [mock_opa_resp, mock_sap_resp]

        payload = {
            "user_id": "usr_99823",
            "user_role": "Finance_Manager",
            "tool_name": "update_credit_limit",
            "parameters": {"account_id": "ACC-88219", "new_limit": 30000},
            "hitl_approval_token": None,
        }
        response = self.client.post("/api/v1/credit", json=payload)
        self.assertEqual(response.status_code, 200)

    @patch("src.proxy_server.requests.post")
    def test_over_threshold_requires_hitl(self, mock_post):
        mock_opa_resp = MagicMock()
        mock_opa_resp.json.return_value = {
            "result": {"allow": False, "require_hitl": True}
        }
        mock_post.return_value = mock_opa_resp

        payload = {
            "user_id": "usr_99823",
            "user_role": "Finance_Manager",
            "tool_name": "update_credit_limit",
            "parameters": {"account_id": "ACC-88219", "new_limit": 85000},
            "hitl_approval_token": None,
        }
        response = self.client.post("/api/v1/credit", json=payload)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error_code"], "POLICY_BREACH_HITL_REQUIRED")

    @patch("src.proxy_server.requests.post")
    def test_unauthorized_role_blocked(self, mock_post):
        mock_opa_resp = MagicMock()
        mock_opa_resp.json.return_value = {"result": {"allow": False, "require_hitl": False}}
        mock_post.return_value = mock_opa_resp

        payload = {
            "user_id": "usr_00001",
            "user_role": "Sales_Rep",
            "tool_name": "update_credit_limit",
            "parameters": {"account_id": "ACC-88219", "new_limit": 10000},
            "hitl_approval_token": None,
        }
        response = self.client.post("/api/v1/credit", json=payload)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error_code"], "POLICY_BREACH_DENIED")

if __name__ == "__main__":
    unittest.main()
