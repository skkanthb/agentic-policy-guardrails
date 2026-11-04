# Failure checks — before fix (2026-11-03, commit 996c4f1)

Payload: P01 from cases.jsonl
`{"user_role":"Finance_Manager","tool_name":"update_credit_limit","parameters":{"account_id":"ACC-1","new_limit":30000},"hitl_approval_token":null}`

## Check 1 — mock ERP stopped, policy engine running
Command: curl -s -X POST http://localhost:8000/api/v1/credit -H 'Content-Type: application/json' -H 'X-Case-Id: FC1-ERP-DOWN' -d '<P01>'
Response:
```
{"status":"SUCCESS","message":"Transaction allowed and processed."}
HTTP 200
```

## Check 2 — policy engine stopped, mock ERP running
Command: curl -s -X POST http://localhost:8000/api/v1/credit -H 'Content-Type: application/json' -H 'X-Case-Id: FC2-OPA-DOWN' -d '<P01>'
Response:
```
{"detail":"Policy engine unreachable: HTTPConnectionPool(host='localhost', port=8181): Max retries exceeded with url: /v1/data/agent/governance (Caused by NewConnectionError(\"HTTPConnection(host='localhost', port=8181): Failed to establish a new connection: [Errno 61] Connection refused\"))"}
HTTP 500
```

# Failure checks — after fix (2026-11-03, commit d4d9bb2)

## Check 1 — mock ERP stopped, policy engine running
Response:
```
{"status":"ERROR","error_code":"ERP_CALL_FAILED","message":"Policy allowed the request, but the ERP call failed (ConnectionError). The write was not confirmed."}
HTTP 502
```

## Check 2 — policy engine stopped, mock ERP running
Response:
```
{"detail":"Policy engine unreachable: HTTPConnectionPool(host='localhost', port=8181): Max retries exceeded with url: /v1/data/agent/governance (Caused by NewConnectionError(\"HTTPConnection(host='localhost', port=8181): Failed to establish a new connection: [Errno 61] Connection refused\"))"}
HTTP 500
```
