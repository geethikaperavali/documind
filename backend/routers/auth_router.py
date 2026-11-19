from fastapi import APIRouter, Depends
from backend.auth import get_current_user
from backend.database import get_supabase_admin
from backend.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/me")
async def get_current_user_profile(user: dict = Depends(get_current_user)):
    """
    Returns the authenticated user's profile and account settings.
    """
    user_id = user["id"]
    email = user["email"]
    
    # Try fetching profile from profiles table
    try:
        admin = get_supabase_admin()
        profile_res = admin.table("profiles").select("*").eq("id", user_id).execute()
        if profile_res.data and len(profile_res.data) > 0:
            profile = profile_res.data[0]
            return {
                "id": user_id,
                "email": email,
                "full_name": profile.get("full_name") or user.get("user_metadata", {}).get("full_name", ""),
                "avatar_url": profile.get("avatar_url") or user.get("user_metadata", {}).get("avatar_url", ""),
                "preferences": profile.get("preferences", {"theme": "light", "notifications": True}),
                "created_at": profile.get("created_at")
            }
    except Exception as e:
        print(f"[AuthRouter] Profile fetch warning: {e}")

    # Fallback from user metadata
    return {
        "id": user_id,
        "email": email,
        "full_name": user.get("user_metadata", {}).get("full_name", email.split("@")[0]),
        "avatar_url": user.get("user_metadata", {}).get("avatar_url", ""),
        "preferences": {"theme": "light", "notifications": True}
    }

@router.get("/config")
async def get_public_auth_config():
    """
    Returns public client configuration needed for frontend Supabase Auth.
    Never exposes service role keys or backend secrets.
    """
    return {
        "supabase_url": settings.SUPABASE_URL,
        "supabase_anon_key": settings.SUPABASE_ANON_KEY,
        "has_gemini_key": bool(settings.GEMINI_API_KEY)
    }
