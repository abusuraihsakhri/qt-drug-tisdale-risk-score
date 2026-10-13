"""
FastAPI REST API Server for Qt Drug Tisdale Risk Score.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from .base import AuditLogger, PHIGuard
from tisdale_qt import calculate_tisdale_score
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Qt Drug Tisdale Risk Score API",
    description="Tisdale QTc risk score and local legacy audit demonstration",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    query: str



class TisdaleAssessment(BaseModel):
    """Only the nine published risk factors; no direct identifiers."""
    model_config = ConfigDict(extra="forbid")
    age: float
    sex: str
    loop_diuretic: bool
    potassium: float
    qtc: float
    acute_mi: bool
    heart_failure: bool
    num_qtdrugs: int
    sepsis: bool


@app.post("/api/score")
def api_score(payload: TisdaleAssessment):
    """Deterministic calculation without transmitting inputs to external services."""
    try:
        return calculate_tisdale_score(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "qt-drug-tisdale-risk-score", "version": "1.0.0"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "RUNNING"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
