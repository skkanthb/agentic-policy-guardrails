import os
import requests
from fastapi import FastAPI, HTTPException, Request, Response

app = FastAPI(title="ACCP Security Proxy (Open-Source Core)")

OPA_URL = os.getenv("OPA_URL", "http://localhost:8181/v1/data/agent/governance")
LIVE_SAP_URL = os.getenv("SAP_GATEWAY_URL", "https://live-sap-gateway.yourcompany.com/api/v1/credit")

# This endpoint performs one action. The caller's tool_name must match it.
ENDPOINT_TOOL = "update_credit_limit"
# Parameters forwarded to the ERP after an allow. Anything else in the request is dropped.
FORWARDED_PARAMETERS = ("account_id", "new_limit")


@app.post("/api/v1/credit")
async def handle_sap_credit_update(request: Request, response: Response):
    try:
        payload = await request.json()
    except ValueError:
        response.status_code = 400
        return {"status": "BLOCKED", "error_code": "INVALID_JSON", "message": "Request body is not valid JSON."}
    if not isinstance(payload, dict):
        response.status_code = 400
        return {"status": "BLOCKED", "error_code": "INVALID_REQUEST", "message": "Request body must be a JSON object."}

    if payload.get("tool_name") != ENDPOINT_TOOL:
        response.status_code = 403
        return {
            "status": "BLOCKED",
            "error_code": "TOOL_NOT_ALLOWED_ON_ENDPOINT",
            "message": f"This endpoint accepts tool_name '{ENDPOINT_TOOL}' only.",
        }

    # The policy evaluates the request exactly as received. No defaults are filled in.
    opa_input = {"input": payload}

    try:
        opa_res = requests.post(OPA_URL, json=opa_input, timeout=5)
        opa_res.raise_for_status()
        result = opa_res.json().get("result", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Policy engine unreachable: {str(e)}")

    params = payload.get("parameters")
    new_limit = params.get("new_limit") if isinstance(params, dict) else None
    print(f"ACCP DECISION | user={payload.get('user_id')} role={payload.get('user_role')} "
          f"tool={payload.get('tool_name')} new_limit={new_limit} "
          f"allow={result.get('allow')} require_hitl={result.get('require_hitl')} "
          f"violations={result.get('violations')}")

    if result.get("allow") is True:
        forward_body = {
            "user_role": payload["user_role"],
            "tool_name": ENDPOINT_TOOL,
            "parameters": {k: params[k] for k in FORWARDED_PARAMETERS},
        }
        print(f"ABOUT TO CALL SAP SANDBOX at {LIVE_SAP_URL} ...")
        try:
            sap_res = requests.post(LIVE_SAP_URL, json=forward_body, headers=dict(request.headers), timeout=10)
        except requests.RequestException as e:
            print(f"SAP SANDBOX CALL FAILED: {e}")
            response.status_code = 502
            return {
                "status": "ERROR",
                "error_code": "ERP_CALL_FAILED",
                "message": f"Policy allowed the request, but the ERP call failed ({type(e).__name__}). The write was not confirmed.",
            }
        print(f"SAP SANDBOX RESPONDED | status={sap_res.status_code} body={sap_res.text[:300]}")
        if not sap_res.ok:
            response.status_code = 502
            return {
                "status": "ERROR",
                "error_code": "ERP_ERROR_RESPONSE",
                "message": f"Policy allowed the request, but the ERP returned HTTP {sap_res.status_code}. The write was not confirmed.",
            }
        try:
            return sap_res.json()
        except ValueError:
            response.status_code = 502
            return {
                "status": "ERROR",
                "error_code": "ERP_INVALID_RESPONSE",
                "message": "Policy allowed the request, but the ERP response was not valid JSON. The write was not confirmed.",
            }

    response.status_code = 403
    violations = sorted(result.get("violations") or [])
    if result.get("require_hitl") is True:
        return {
            "status": "BLOCKED",
            "error_code": "POLICY_BREACH_HITL_REQUIRED",
            "message": "Action exceeds the automatic approval threshold and requires human approval. "
                       "Approval tokens are not verified by this prototype, so the request cannot proceed here.",
        }
    return {
        "status": "BLOCKED",
        "error_code": "POLICY_BREACH_DENIED",
        "message": "Action denied by security policy.",
        "violations": violations,
    }
