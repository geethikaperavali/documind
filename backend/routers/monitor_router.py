import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.auth import get_current_user
from backend.database import get_supabase_admin
from backend.services.monitor_service import monitor_service

router = APIRouter(prefix="/monitor", tags=["Live Monitor"])

class AddTopicRequest(BaseModel):
    topic: str
    frequency: str = "daily" # "hourly", "daily", "weekly"

class UpdateTopicRequest(BaseModel):
    topic: Optional[str] = None
    frequency: Optional[str] = None
    status: Optional[str] = None # "active", "paused"

class CheckTopicRequest(BaseModel):
    topic: Optional[str] = "Global regulatory & AI developments"
    topic_id: Optional[str] = None

_memory_topics: Dict[str, Dict[str, Any]] = {}
_memory_logs: List[Dict[str, Any]] = []

@router.get("/topics")
async def list_monitored_topics(
    user: dict = Depends(get_current_user)
):
    """
    Lists user's tracked topics and recent monitor alerts with memory fallback.
    """
    try:
        admin = get_supabase_admin()
        res = admin.table("watchlist_topics").select("*").eq("user_id", user["id"]).order("created_at", desc=True).execute()
        if res.data:
            for t in res.data:
                if "last_checked_at" in t and not t.get("last_checked"):
                    t["last_checked"] = t["last_checked_at"]
            return {"topics": res.data}
    except Exception:
        pass

    user_topics = [t for t in _memory_topics.values() if t.get("user_id") == user["id"]]
    for t in user_topics:
        if "last_checked_at" in t and not t.get("last_checked"):
            t["last_checked"] = t["last_checked_at"]
    return {"topics": user_topics}

@router.post("/topics")
async def add_monitored_topic(
    req: AddTopicRequest,
    user: dict = Depends(get_current_user)
):
    """
    Adds a new topic to the user's live surveillance watchlist and triggers an initial sweep.
    """
    if not req.topic.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Topic cannot be empty.")

    topic_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": topic_id,
        "user_id": user["id"],
        "topic": req.topic.strip(),
        "frequency": req.frequency,
        "status": "active",
        "created_at": now,
        "last_checked_at": now,
        "last_checked": now
    }
    _memory_topics[topic_id] = record

    try:
        admin = get_supabase_admin()
        db_record = {
            "id": topic_id,
            "user_id": user["id"],
            "topic": req.topic.strip(),
            "frequency": req.frequency,
            "status": "active",
            "created_at": now,
            "last_checked_at": now
        }
        admin.table("watchlist_topics").insert(db_record).execute()
    except Exception as e:
        print(f"[MonitorRouter] DB insert note: {e}")

    # Immediately run first check
    initial_check = monitor_service.check_topic_updates(topic=req.topic.strip(), user_id=user["id"], topic_id=topic_id)
    _memory_logs.append({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "topic": req.topic.strip(),
        "change_level": initial_check.get("change_level", "Routine Update"),
        "headline": initial_check.get("headline", "Surveillance sweep completed."),
        "log_data": initial_check,
        "created_at": now
    })
    return {"message": "Topic added to live watchlist", "topic": record, "initial_sweep": initial_check}

@router.put("/topics/{topic_id}")
async def update_monitored_topic(
    topic_id: str,
    payload: UpdateTopicRequest,
    user: dict = Depends(get_current_user)
):
    """
    Updates a topic's title, frequency, or toggles pause/resume status.
    """
    if topic_id in _memory_topics:
        if payload.topic:
            _memory_topics[topic_id]["topic"] = payload.topic.strip()
        if payload.frequency:
            _memory_topics[topic_id]["frequency"] = payload.frequency.strip()
        if payload.status:
            _memory_topics[topic_id]["status"] = payload.status.strip()

    admin = get_supabase_admin()
    update_data = {}
    if payload.topic:
        update_data["topic"] = payload.topic.strip()
    if payload.frequency:
        update_data["frequency"] = payload.frequency.strip()
    if payload.status:
        update_data["status"] = payload.status.strip()

    try:
        res = admin.table("watchlist_topics").update(update_data).eq("id", topic_id).eq("user_id", user["id"]).execute()
        if res.data:
            return {"success": True, "topic": res.data[0]}
    except Exception:
        pass

    if topic_id in _memory_topics:
        return {"success": True, "topic": _memory_topics[topic_id]}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

@router.delete("/topics/{topic_id}")
async def delete_monitored_topic(
    topic_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Permanently deletes a tracked topic and its associated logs.
    """
    _memory_topics.pop(topic_id, None)

    admin = get_supabase_admin()
    try:
        try:
            admin.table("monitor_logs").delete().eq("user_id", user["id"]).eq("log_data->>topic_id", topic_id).execute()
        except Exception:
            pass
        admin.table("watchlist_topics").delete().eq("id", topic_id).eq("user_id", user["id"]).execute()
    except Exception:
        pass

    return {"success": True, "message": "Topic deleted successfully."}

@router.post("/check")
async def trigger_topic_sweep(
    req: Optional[CheckTopicRequest] = None,
    user: dict = Depends(get_current_user)
):
    """
    Performs an immediate live web sweep for a tracked topic and returns delta findings.
    """
    topic_text = (req.topic.strip() if req and req.topic else "General regulatory and technology updates")
    topic_id = (req.topic_id if req else None)

    res = monitor_service.check_topic_updates(
        topic=topic_text,
        user_id=user["id"],
        topic_id=topic_id
    )

    now = datetime.now(timezone.utc).isoformat()
    _memory_logs.append({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "topic": topic_text,
        "change_level": res.get("change_level", "Routine Update"),
        "headline": res.get("headline", "Surveillance sweep completed."),
        "log_data": res,
        "created_at": now
    })

    if topic_id:
        if topic_id in _memory_topics:
            _memory_topics[topic_id]["last_checked_at"] = now
            _memory_topics[topic_id]["last_checked"] = now
        try:
            admin = get_supabase_admin()
            admin.table("watchlist_topics").update({"last_checked_at": now}).eq("id", topic_id).eq("user_id", user["id"]).execute()
        except Exception:
            pass

    return res

@router.get("/logs")
async def list_monitor_logs(
    topic: Optional[str] = None,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """
    Retrieves surveillance history logs across user watchlists.
    """
    try:
        admin = get_supabase_admin()
        q = admin.table("monitor_logs").select("*").eq("user_id", user["id"])
        if topic:
            q = q.eq("topic", topic)
        res = q.order("created_at", desc=True).limit(limit).execute()
        if res.data:
            return {"logs": res.data}
    except Exception:
        pass

    user_logs = [l for l in _memory_logs if l.get("user_id") == user["id"]]
    if topic:
        user_logs = [l for l in user_logs if l.get("topic") == topic]
    return {"logs": user_logs[:limit]}
