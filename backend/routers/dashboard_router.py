from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user
from backend.database import get_supabase_admin

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def format_bytes(bytes_num: int) -> str:
    if bytes_num < 1024:
        return f"{bytes_num} B"
    elif bytes_num < 1024 * 1024:
        return f"{round(bytes_num / 1024, 1)} KB"
    elif bytes_num < 1024 * 1024 * 1024:
        return f"{round(bytes_num / (1024 * 1024), 2)} MB"
    else:
        return f"{round(bytes_num / (1024 * 1024 * 1024), 2)} GB"

@router.get("/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    """
    Returns dynamic dashboard metrics computed from actual database records:
    - Total Documents
    - Storage Used
    - Questions Asked
    - Recent Documents
    - Recent Activity log
    """
    user_id = user["id"]
    admin = get_supabase_admin()

    try:
        # 1. Total Documents & Storage calculation
        docs_res = admin.table("documents") \
            .select("id, name, file_type, file_size, status, chunk_count, created_at") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .execute()
        
        documents = docs_res.data or []
        total_documents = len(documents)
        total_storage_bytes = sum(doc.get("file_size", 0) for doc in documents)
        
        # 2. Questions Asked calculation (count messages where role = 'user')
        msgs_res = admin.table("messages") \
            .select("id, content, created_at") \
            .eq("user_id", user_id) \
            .eq("role", "user") \
            .order("created_at", desc=True) \
            .execute()

        user_messages = msgs_res.data or []
        questions_asked = len(user_messages)

        # 3. Recent Documents (top 5)
        recent_documents = documents[:5]

        # 4. Recent Activity (Chronological combination of uploads and queries)
        activity_items = []
        for doc in documents[:5]:
            activity_items.append({
                "type": "upload",
                "title": f"Uploaded {doc.get('name')}",
                "description": f"{doc.get('file_type', '').upper()} • {format_bytes(doc.get('file_size', 0))} • {doc.get('status', 'processing').capitalize()}",
                "timestamp": doc.get("created_at"),
                "badge": doc.get("status", "processing")
            })

        for msg in user_messages[:5]:
            q_snippet = msg.get("content", "")
            if len(q_snippet) > 60:
                q_snippet = q_snippet[:60] + "..."
            activity_items.append({
                "type": "query",
                "title": "Asked DocuMind AI",
                "description": f'"{q_snippet}"',
                "timestamp": msg.get("created_at"),
                "badge": "question"
            })

        # Sort activities descending by timestamp
        activity_items.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        recent_activity = activity_items[:8]

        return {
            "total_documents": total_documents,
            "storage_used_bytes": total_storage_bytes,
            "storage_used_formatted": format_bytes(total_storage_bytes),
            "questions_asked": questions_asked,
            "recent_documents": recent_documents,
            "recent_activity": recent_activity
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate dashboard statistics: {str(e)}"
        )
