from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user
from backend.database import get_supabase_admin

router = APIRouter(prefix="/profile", tags=["User Profile"])

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

@router.get("")
async def get_profile(user: dict = Depends(get_current_user)):
    """
    Returns user profile details from the profiles table.
    """
    user_id = user["id"]
    admin = get_supabase_admin()

    try:
        res = admin.table("profiles").select("*").eq("id", user_id).execute()
        if res.data and len(res.data) > 0:
            return {"profile": res.data[0]}
    except Exception as e:
        print(f"[ProfileRouter] Get profile error: {e}")

    # Fallback if profile row not created yet
    return {
        "profile": {
            "id": user_id,
            "email": user["email"],
            "full_name": user.get("user_metadata", {}).get("full_name", user["email"].split("@")[0]),
            "avatar_url": user.get("user_metadata", {}).get("avatar_url", ""),
            "preferences": {"theme": "light", "notifications": True}
        }
    }

@router.put("")
async def update_profile(
    payload: UpdateProfileRequest,
    user: dict = Depends(get_current_user)
):
    """
    Updates profile full name, avatar URL, and preferences.
    """
    user_id = user["id"]
    admin = get_supabase_admin()

    update_fields = {}
    if payload.full_name is not None:
        update_fields["full_name"] = payload.full_name.strip()
    if payload.avatar_url is not None:
        update_fields["avatar_url"] = payload.avatar_url.strip()
    if payload.preferences is not None:
        update_fields["preferences"] = payload.preferences

    if not update_fields:
        return {"message": "No changes specified."}

    try:
        res = admin.table("profiles").update(update_fields).eq("id", user_id).execute()
        return {
            "success": True,
            "message": "Profile updated successfully.",
            "profile": res.data[0] if res.data else update_fields
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")
