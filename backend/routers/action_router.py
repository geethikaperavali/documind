from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.auth import get_current_user
from backend.services.action_service import action_service

router = APIRouter(prefix="/action", tags=["Action Studio"])

class GenerateArtifactRequest(BaseModel):
    artifact_type: str # "plan", "tasks", "checklist", "business_analysis", "report", "study"
    source_type: str = "document" # "document", "research", "custom"
    source_id: Optional[str] = None
    custom_instructions: Optional[str] = None

class UpdateArtifactRequest(BaseModel):
    title: Optional[str] = None
    artifact_data: Optional[Dict[str, Any]] = None

@router.post("/generate")
async def generate_action_artifact(
    req: GenerateArtifactRequest,
    user: dict = Depends(get_current_user)
):
    """
    Transforms research dossiers or document knowledge into:
    - Implementation Plan
    - Task Breakdown (WBS)
    - Action & Compliance Checklist
    - Strategic & Risk Analysis (SWOT)
    - Executive Decision Report
    - Study Material & Flashcards
    Automatically persists to action_artifacts table.
    """
    valid_types = {"plan", "tasks", "checklist", "business_analysis", "report", "study"}
    if req.artifact_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid artifact_type. Must be one of: {', '.join(valid_types)}"
        )

    artifact = action_service.generate_action_artifact(
        artifact_type=req.artifact_type,
        source_type=req.source_type,
        source_id=req.source_id,
        user_id=user["id"],
        custom_instructions=req.custom_instructions
    )
    return artifact

@router.get("/artifacts")
async def list_action_artifacts(
    user: dict = Depends(get_current_user)
):
    """
    Lists all saved action artifacts belonging to the authenticated user.
    """
    artifacts = action_service.list_artifacts(user_id=user["id"])
    return {"artifacts": artifacts}

@router.get("/artifacts/{artifact_id}")
async def get_action_artifact(
    artifact_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Retrieves a single action artifact with full details.
    """
    artifact = action_service.get_artifact(artifact_id=artifact_id, user_id=user["id"])
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action artifact not found.")
    return artifact

@router.put("/artifacts/{artifact_id}")
async def update_action_artifact(
    artifact_id: str,
    payload: UpdateArtifactRequest,
    user: dict = Depends(get_current_user)
):
    """
    Updates an action artifact title or modified structure.
    """
    updated = action_service.update_artifact(
        artifact_id=artifact_id,
        user_id=user["id"],
        title=payload.title,
        artifact_data=payload.artifact_data
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Could not update artifact.")
    return {"success": True, "artifact": updated}

@router.delete("/artifacts/{artifact_id}")
async def delete_action_artifact(
    artifact_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Deletes an action artifact.
    """
    success = action_service.delete_artifact(artifact_id=artifact_id, user_id=user["id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete artifact.")
    return {"success": True, "message": "Artifact deleted successfully."}
