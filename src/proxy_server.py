import os
import requests
from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="ACCP Security Proxy")

OPA_URL = os.getenv("OPA_URL", "http://localhost:8181/v1/data/sap/sox")
LIVE_SAP_URL = os.getenv("SAP_GATEWAY_URL", "https://live-sap-gateway.yourcompany.com/api/v1/credit")

@app.post("/api/v1/credit")
async def handle_sap_credit_update(request: Request):
    payload = await request.json()
    
    # 1. Format payload for OPA evaluation
    opa_input = {
        "input": {
            "action": "update_credit_limit",
            "payload": payload
        }
    }
    
    # 2. Query ACCP Policy Engine
    try:
        opa_response = requests.post(OPA_URL, json=opa_input).json()
        result = opa_response.get("result", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Policy engine unreachable: {str(e)}")
    
    # 3. Decision Enforcement
    if result.get("allow"):
        # Forward payload directly to live SAP instance
        sap_res = requests.post(LIVE_SAP_URL, json=payload, headers=dict(request.headers))
        return sap_res.json()
    
    elif result.get("requires_hitl"):
        # Intercept and return security policy breach error
        return {
            "status": "BLOCKED",
            "error_code": "POLICY_BREACH_HITL_REQUIRED",
            "message": result.get("deny_reason", "Action requires managerial consent.")
        }, 403

    return {"status": "BLOCKED", "message": "Unauthorized action."}, 403
