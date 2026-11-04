# Mock ERP target. Logs every body it receives to target_received.jsonl.
# Run: uvicorn mock_target:app --port 9000
import json, time
from fastapi import FastAPI, Request
app = FastAPI()
@app.post("/api/v1/credit")
async def credit(request: Request):
    body = await request.json()
    with open("target_received.jsonl", "a") as f:
        f.write(json.dumps({"ts": time.time(), "case_id": request.headers.get("x-case-id"), "body": body}) + "\n")
    return {"status": "SUCCESS", "source": "mock_target"}
