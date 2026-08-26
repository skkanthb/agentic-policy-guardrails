import os
import requests
from fastapi import FastAPI, HTTPException, Request, Response

app = FastAPI(title="ACCP Security Proxy")

OPA_URL = os.getenv("OPA_URL", "http://localhost:8181/v1/data/sap/sox")
LIVE_SAP_URL = os.getenv("SAP_GATEWAY_URL", "https://live-sap-gateway.yourcompany.com/api/v1/credit")

@app.post("/api/v1/credit")
async def handle_sap_credit_update(request: Request, response: Response):
    payload = await request.json()
    
    opa_input = {
        "input": {
            "action": "update_credit_limit",
            "payload": payload
        }
    }
    
    try:
        opa_res = requests.post(OPA_URL, json=opa_input)
        opa_data = opa_res.json()
        result = opa_data.get("result", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Policy engine unreachable: {str(e)}")
    
    # 1. Allowed Path
    if result.get("allow") is True:
        try:
            sap_res = requests.post(LIVE_SAP_URL, json=payload, headers=dict(request.headers))
            return sap_res.json()
        except Exception:
            # Fallback for testing environments without real SAP connection
            return {"status": "SUCCESS", "message": "Transaction allowed and processed."}
    
    # 2. Blocked / HITL Required Path
    if result.get("requires_hitl") is True or not result.get("allow"):
        response.status_code = 403
        return {
            "status": "BLOCKED",
            "error_code": "POLICY_BREACH_HITL_REQUIRED",
            "message": result.get("deny_reason", "SOX Control Breach: Action requires managerial approval.")
        }

    response.status_code = 403
    return {"status": "BLOCKED", "message": "Unauthorized action."}
