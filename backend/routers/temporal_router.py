from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.auth import get_current_user
from backend.services.temporal_intelligence import temporal_service

router = APIRouter(prefix="/temporal", tags=["Temporal Intelligence"])

class TemporalVerifyRequest(BaseModel):
    query: str
    historical_context: Optional[str] = None

class DocumentAuditRequest(BaseModel):
    document_id: str

@router.post("/verify")
async def verify_statute_or_scheme(
    req: TemporalVerifyRequest,
    user: dict = Depends(get_current_user)
):
    """
    Verifies the present-day legal, regulatory, or empirical status of a provision/law/scheme.
    Returns 7-part standardized temporal verdict with official citations.
    """
    if not req.query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty.")
    
    verdict = temporal_service.verify_temporal_status(
        query=req.query.strip(),
        historical_context=req.historical_context
    )
    return verdict

@router.post("/audit-document")
async def audit_document(
    req: DocumentAuditRequest,
    user: dict = Depends(get_current_user)
):
    """
    Scans an uploaded document for time-sensitive provisions (repealed acts, amended sections, expired dates)
    and returns a Temporal Health Scorecard.
    """
    audit = temporal_service.audit_document_temporality(
        document_id=req.document_id,
        user_id=user["id"]
    )
    if "error" in audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=audit["error"])
    return audit
