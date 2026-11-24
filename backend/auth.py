from typing import Optional, Dict, Any
import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.config import settings
from backend.database import get_supabase_admin

security = HTTPBearer(auto_error=False)

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency to verify Supabase JWT token and extract user information.
    Checks bearer token via Supabase Auth API, or PyJWT if configured.
    Also extracts optional custom Gemini API key from request headers.
    """
    custom_gemini_key = request.headers.get("X-Gemini-API-Key")
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Method 1: Local JWT decoding if SUPABASE_JWT_SECRET is set (fast & offline)
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_aud": False} # Supabase tokens usually have aud 'authenticated'
            )
            user_id = payload.get("sub")
            email = payload.get("email", "")
            if user_id:
                return {
                    "id": user_id,
                    "email": email,
                    "role": payload.get("role", "authenticated"),
                    "user_metadata": payload.get("user_metadata", {}),
                    "token": token,
                    "custom_gemini_key": custom_gemini_key
                }
        except jwt.PyJWTError:
            # Fall through to Supabase API verification
            pass

    # Method 2: Verify against Supabase Auth API directly
    try:
        admin = get_supabase_admin()
        user_response = admin.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = user_response.user
        return {
            "id": str(user.id),
            "email": user.email or "",
            "role": user.role or "authenticated",
            "user_metadata": user.user_metadata or {},
            "token": token,
            "custom_gemini_key": custom_gemini_key
        }
    except HTTPException:
        raise
    except Exception as e:
        # Check if error message indicates invalid token
        err_msg = str(e).lower()
        if "expired" in err_msg or "invalid" in err_msg or "jwt" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
