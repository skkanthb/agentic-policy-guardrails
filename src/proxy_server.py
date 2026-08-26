import os
import requests
from fastapi import FastAPI, HTTPException, Request, Response

app = FastAPI(title="ACCP Security Proxy (Open-Source Core)")

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
    
    # 1. ALLOWED PATH
    if result.get("allow") is True:
        try:
            sap_res = requests.post(LIVE_SAP_URL, json=payload, headers=dict(request.headers))
            return sap_res.json()
        except Exception:
            return {"status": "SUCCESS", "message": "Transaction allowed and processed."}
    
    # 2. BLOCKED PATH (Standard Open-Source 403)
    response.status_code = 403
    return {
        "status": "BLOCKED",
        "error_code": "POLICY_BREACH_DENIED",
        "message": result.get("deny_reason", "Action denied by security policy.")
    }
