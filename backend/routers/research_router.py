from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.auth import get_current_user
from backend.services.research_service import research_service
from backend.services.source_registry import source_registry
from backend.services.ai_intelligence import ai_intelligence_service
from backend.database import get_supabase_admin

router = APIRouter(prefix="/research", tags=["Research Studio"])

class ResearchQueryRequest(BaseModel):
    topic: str
    domain: Optional[str] = "general_universal"
    depth: Optional[str] = "comprehensive" # "brief", "comprehensive", "regulatory"

class AIIntelligenceRequest(BaseModel):
    query: str
    include_web_crawl: Optional[bool] = True

@router.post("/query")
async def run_research_query(
    req: ResearchQueryRequest,
    user: dict = Depends(get_current_user)
):
    """
    Executes live universal web research across 12+ domains, finds authoritative sources,
    enriches with Source Registry provenance, and returns a structured research dossier
    with clickable citations and retrieval timestamps.
    """
    if not req.topic.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Research topic cannot be empty.")

    report = research_service.conduct_research(
        topic=req.topic.strip(),
        user_id=user["id"],
        domain=req.domain or "general_universal",
        depth=req.depth or "comprehensive"
    )
    return report

@router.get("/sources/registry")
async def get_source_registry(
    domain: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Returns the catalog of registered authoritative sources, domain breakdowns,
    freshness intervals, and reliability verification standards.
    """
    domains = source_registry.list_domains()
    sources = source_registry.list_sources(domain=domain)
    return {
        "domains": domains,
        "total_sources": len(sources),
        "sources": sources
    }

@router.post("/ai-intelligence")
async def get_ai_model_intelligence(
    req: AIIntelligenceRequest,
    user: dict = Depends(get_current_user)
):
    """
    Dedicated AI Industry Intelligence Endpoint:
    Provides model version comparisons, token pricing, context windows,
    vendor claims vs independent evaluations (LMSYS Chatbot Arena, SWE-bench Verified),
    and deprecation tracking.
    """
    if not req.query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI query cannot be empty.")

    matrix = ai_intelligence_service.generate_model_comparison_matrix(query=req.query.strip())
    return matrix

@router.get("/history")
async def list_research_history(
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Lists user's saved research dossiers with optional keyword search.
    """
    reports = research_service.list_saved_reports(user_id=user["id"], search_query=q)
    return {"reports": reports}

@router.delete("/history")
async def clear_research_history(
    user: dict = Depends(get_current_user)
):
    """
    Clears all research history for the authenticated user.
    """
    success = research_service.clear_all_history(user_id=user["id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to clear research history.")
    return {"success": True, "message": "Research history cleared."}

@router.get("/{report_id}")
async def get_research_report(
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Retrieves a specific research report.
    """
    report = research_service.get_saved_report(report_id=report_id, user_id=user["id"])
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research report not found.")
    return report

@router.delete("/{report_id}")
async def delete_research_report(
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Deletes an individual research report.
    """
    success = research_service.delete_report(report_id=report_id, user_id=user["id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete report.")
    return {"success": True, "message": "Research report deleted."}
