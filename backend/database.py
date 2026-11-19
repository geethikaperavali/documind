from typing import Optional
from supabase import create_client, Client
from backend.config import settings

_admin_client: Optional[Client] = None

def get_supabase_admin() -> Client:
    """
    Returns a cached Supabase admin client using the service role key.
    Used for backend processing, background chunk embedding storage, and administrative calls.
    """
    global _admin_client
    if _admin_client is not None:
        return _admin_client

    if not settings.SUPABASE_URL:
        raise ValueError("SUPABASE_URL is not configured in environment variables.")

    # Try service role key first, then anon key as fallback
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    if not key:
        raise ValueError("Neither SUPABASE_SERVICE_ROLE_KEY nor SUPABASE_ANON_KEY is configured.")

    _admin_client = create_client(settings.SUPABASE_URL, key)
    return _admin_client

def get_supabase_client_for_user(access_token: str) -> Client:
    """
    Creates a scoped Supabase client with the user's JWT access token.
    This ensures queries run under the user's specific Row Level Security (RLS) policies.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be configured.")

    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    # Attach user authorization header for RLS
    client.postgrest.auth(access_token)
    return client
