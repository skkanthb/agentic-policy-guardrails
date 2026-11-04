import unittest
from unittest.mock import patch, MagicMock

import requests
from fastapi.testclient import TestClient

from src.proxy_server import app


def opa_response(result):
    res = MagicMock()
    res.json.return_value = {"result": result}
    return res


def erp_response(status_code=200, body=None):
    res = MagicMock()
    res.status_code = status_code
    res.ok = status_code < 400
    res.text = ""
    res.json.return_value = body if body is not None else {"status": "SUCCESS"}
    return res


VALID = {
    "user_role": "Finance_Manager",
    "tool_name": "update_credit_limit",
    "parameters": {"account_id": "ACC-1", "new_limit": 30000},
    "hitl_approval_token": None,
}


class TestProxyEdgeCases(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("src.proxy_server.requests.post")
    def test_other_tool_name_refused_before_policy(self, mock_post):
        payload = dict(VALID, tool_name="get_customer_balance")
        response = self.client.post("/api/v1/credit", json=payload)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error_code"], "TOOL_NOT_ALLOWED_ON_ENDPOINT")
        mock_post.assert_not_called()

    @patch("src.proxy_server.requests.post")
    def test_policy_receives_request_as_sent(self, mock_post):
        payload = dict(VALID, new_limit=75000)
        mock_post.return_value = opa_response({"allow": False, "require_hitl": False,
                                               "violations": ["unknown top-level field"]})
        response = self.client.post("/api/v1/credit", json=payload)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(mock_post.call_args.kwargs["json"], {"input": payload})
        self.assertEqual(response.json()["violations"], ["unknown top-level field"])

    @patch("src.proxy_server.requests.post")
    def test_erp_receives_only_checked_fields(self, mock_post):
        payload = dict(VALID, user_id="usr_1", hitl_approval_token="approved")
        mock_post.side_effect = [opa_response({"allow": True, "require_hitl": False}), erp_response()]
        response = self.client.post("/api/v1/credit", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_post.call_args_list[1].kwargs["json"], {
            "user_role": "Finance_Manager",
            "tool_name": "update_credit_limit",
            "parameters": {"account_id": "ACC-1", "new_limit": 30000},
        })

    @patch("src.proxy_server.requests.post")
    def test_erp_unreachable_is_not_reported_as_success(self, mock_post):
        mock_post.side_effect = [opa_response({"allow": True, "require_hitl": False}),
                                 requests.ConnectionError("refused")]
        response = self.client.post("/api/v1/credit", json=VALID)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error_code"], "ERP_CALL_FAILED")

    @patch("src.proxy_server.requests.post")
    def test_erp_error_status_is_not_reported_as_success(self, mock_post):
        mock_post.side_effect = [opa_response({"allow": True, "require_hitl": False}), erp_response(500)]
        response = self.client.post("/api/v1/credit", json=VALID)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error_code"], "ERP_ERROR_RESPONSE")

    @patch("src.proxy_server.requests.post")
    def test_policy_engine_unreachable_fails_closed(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("refused")
        response = self.client.post("/api/v1/credit", json=VALID)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(mock_post.call_count, 1)

    @patch("src.proxy_server.requests.post")
    def test_invalid_json_rejected(self, mock_post):
        response = self.client.post("/api/v1/credit", content=b"not json",
                                    headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "INVALID_JSON")
        mock_post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
