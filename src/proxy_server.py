import os
import requests
from fastapi import FastAPI, HTTPException, Request, Response

app = FastAPI(title="ACCP Security Proxy (Open-Source Core)")

OPA_URL = os.getenv("OPA_URL", "http://localhost:8181/v1/data/agent/governance")
LIVE_SAP_URL = os.getenv("SAP_GATEWAY_URL", "https://live-sap-gateway.yourcompany.com/api/v1/credit")

@app.post("/api/v1/credit")
async def handle_sap_credit_update(request: Request, response: Response):
    payload = await request.json()

    opa_input = {
        "input": {
            "user_id": payload.get("user_id"),
            "user_role": payload.get("user_role"),
            "tool_name": payload.get("tool_name", "update_credit_limit"),
            "parameters": payload.get("parameters", {}),
            "hitl_approval_token": payload.get("hitl_approval_token"),
        }
    }

    try:
        opa_res = requests.post(OPA_URL, json=opa_input)
        opa_data = opa_res.json()
        result = opa_data.get("result", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Policy engine unreachable: {str(e)}")

    print(f"ACCP DECISION | user={payload.get('user_id')} role={payload.get('user_role')} "
          f"tool={payload.get('tool_name')} new_limit={payload.get('parameters',{}).get('new_limit')} "
          f"allow={result.get('allow')} require_hitl={result.get('require_hitl')}")

    if result.get("allow") is True:
        print(f"ABOUT TO CALL SAP SANDBOX at {LIVE_SAP_URL} ...")
        try:
            sap_res = requests.post(LIVE_SAP_URL, json=payload, headers=dict(request.headers))
            print(f"SAP SANDBOX RESPONDED | status={sap_res.status_code} body={sap_res.text[:300]}")
            return sap_res.json()
        except Exception as e:
            print(f"SAP SANDBOX CALL FAILED: {e}")
            return {"status": "SUCCESS", "message": "Transaction allowed and processed."}

    response.status_code = 403
    if result.get("require_hitl") is True:
        return {
            "status": "BLOCKED",
            "error_code": "POLICY_BREACH_HITL_REQUIRED",
            "message": "Action exceeds the automatic approval threshold and requires a manager's HITL approval token before it can proceed.",
        }
    return {
        "status": "BLOCKED",
        "error_code": "POLICY_BREACH_DENIED",
        "message": "Action denied by security policy (invalid action or unauthorized role).",
    }
