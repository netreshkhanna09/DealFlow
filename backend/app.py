import os
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

# Load environment variables from .env if present
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from orchestrator import orchestrator
from database import fetch_recent_negotiations, fetch_audit_trail

app = FastAPI(
    title="DealFlow API",
    description="Razorpay AI Buildathon Track 01 - Two-sided Agentic Commerce & Negotiation Platform",
    version="1.0.0"
)

from llm_engine import set_llm_api_key, ACTIVE_LLM_CONFIG

class LLMKeyRequest(BaseModel):
    api_key: str
    provider: Optional[str] = "auto"

@app.post("/api/settings/llm-key")
def update_llm_key(req: LLMKeyRequest):
    if not req.api_key or len(req.api_key.strip()) < 5:
        raise HTTPException(status_code=400, detail="Invalid LLM API Key.")
    set_llm_api_key(req.api_key, req.provider)
    return {
        "status": "success",
        "message": "LLM API Key updated successfully. All agent decisions will now be generated using live LLM inference!",
        "has_groq": bool(ACTIVE_LLM_CONFIG["groq_api_key"]),
        "has_openai": bool(ACTIVE_LLM_CONFIG["openai_api_key"]),
        "has_gemini": bool(ACTIVE_LLM_CONFIG["gemini_api_key"])
    }

@app.get("/api/settings/llm-status")
def get_llm_status():
    return {
        "has_groq": bool(ACTIVE_LLM_CONFIG["groq_api_key"]),
        "has_openai": bool(ACTIVE_LLM_CONFIG["openai_api_key"]),
        "has_gemini": bool(ACTIVE_LLM_CONFIG["gemini_api_key"]),
        "is_active": bool(ACTIVE_LLM_CONFIG["groq_api_key"] or ACTIVE_LLM_CONFIG["openai_api_key"] or ACTIVE_LLM_CONFIG["gemini_api_key"])
    }

class NegotiateRequest(BaseModel):
    user_prompt: str
    simulate_risk_veto: bool = False
    simulate_payment_fail: bool = False

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "DealFlow Multi-Agent Negotiation Engine",
        "track": "Razorpay AI Buildathon Track 01 - AI Growth & Agentic Commerce"
    }

@app.get("/api/catalog")
def get_catalog():
    catalog_path = os.path.join(os.path.dirname(__file__), "catalog.json")
    with open(catalog_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/negotiate")
def start_negotiation(req: NegotiateRequest):
    if not req.user_prompt or len(req.user_prompt.strip()) < 3:
        raise HTTPException(status_code=400, detail="Please enter a valid product request or budget preference.")
    
    result = orchestrator.run_negotiation(
        user_prompt=req.user_prompt,
        simulate_risk_veto=req.simulate_risk_veto,
        simulate_payment_fail=req.simulate_payment_fail
    )
    return result

@app.get("/api/negotiations")
def list_negotiations(limit: int = 15):
    return fetch_recent_negotiations(limit=limit)

@app.get("/api/negotiation/{negotiation_id}/audit")
def get_audit(negotiation_id: str):
    trail = fetch_audit_trail(negotiation_id)
    if not trail:
        raise HTTPException(status_code=404, detail="Audit trail not found for this negotiation.")
    return trail

# Mount Frontend static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
