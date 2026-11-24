from typing import Optional
from fastapi import APIRouter, Depends, Query
from backend.auth import get_current_user
from backend.services.explorer_service import explorer_service

router = APIRouter(prefix="/explorer", tags=["Knowledge Explorer"])

@router.get("/graph")
async def get_knowledge_graph(
    document_id: Optional[str] = Query(None, description="Optional document ID or 'all'"),
    refresh: bool = Query(False, description="Force re-extraction bypassing cache"),
    user: dict = Depends(get_current_user)
):
    """
    Extracts entities (statutes, organizations, people, concepts, temporal dates)
    and relationships across user documents to render the interactive Knowledge Graph.
    Uses memory cache unless refresh=true is requested.
    """
    graph = explorer_service.extract_document_knowledge_graph(
        document_id=document_id,
        user_id=user["id"],
        refresh=refresh
    )
    return graph
