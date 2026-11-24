from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.auth import get_current_user
from backend.services.compare_service import compare_service

router = APIRouter(prefix="/compare", tags=["Compare & Verify"])

class CompareDocsRequest(BaseModel):
    doc_a_id: str
    doc_b_id: str

class CompareWebRequest(BaseModel):
    document_id: str

@router.post("/documents")
async def compare_two_documents(
    req: CompareDocsRequest,
    user: dict = Depends(get_current_user)
):
    """
    Compares two uploaded documents, identifying changed clauses, conflicting claims, and omissions.
    """
    res = compare_service.compare_documents(
        doc_a_id=req.doc_a_id,
        doc_b_id=req.doc_b_id,
        user_id=user["id"]
    )
    if "error" in res:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res["error"])
    return res

@router.post("/web")
async def compare_document_with_live_world(
    req: CompareWebRequest,
    user: dict = Depends(get_current_user)
):
    """
    Compares an uploaded document against current live official web reality (repealed laws, changed rules, etc.).
    """
    res = compare_service.compare_document_against_web(
        doc_id=req.document_id,
        user_id=user["id"]
    )
    if "error" in res:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res["error"])
    return res
