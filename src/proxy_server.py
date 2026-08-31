import os
import requests
from fastapi import FastAPI, HTTPException, Request, Response

app = FastAPI(title="ACCP Security Proxy (Open-Source Core)")

# Points at the agent.governance policy (policies/agent_governance.rego),
# which supports role checks AND a Human-in-the-Loop approval token —
# unlike the older sap.sox policy, which could only ever say "no" once
# a request was over the threshold.
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181/v1/data/agent/governance")
LIVE_SAP_URL = os.getenv("SAP_GATEWAY_URL", "https://live-sap-gateway.yourcompany.com/api/v1/credit")

@app.post("/api/v1/credit")
async def handle_sap_credit_update(request: Request, response: Response):
    payload = await request.json()

    # This is the shape policies/agent_governance.rego actually expects —
    # it matches examples/input_test.json exactly.
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

    # 1. ALLOWED PATH
    if result.get("allow") is True:
        try:
            sap_res = requests.post(LIVE_SAP_URL, json=payload, headers=dict(request.headers))
            return sap_res.json()
        except Exception:
            return {"status": "SUCCESS", "message": "Transaction allowed and processed."}

    # 2. BLOCKED / ESCALATED PATH
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
    
