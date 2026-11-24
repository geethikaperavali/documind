import asyncio
from datetime import datetime, timezone, timedelta
from backend.database import get_supabase_admin
from backend.services.monitor_service import monitor_service

async def run_surveillance_worker():
    """
    Background worker that continuously monitors active surveillance watchlist topics.
    Evaluates topic frequency (hourly, daily, weekly) and triggers automated delta checks.
    """
    await asyncio.sleep(10) # Grace period for app startup
    print("[SurveillanceScheduler] Background surveillance worker started.", flush=True)

    while True:
        try:
            admin = get_supabase_admin()
            res = admin.table("watchlist_topics").select("*").eq("status", "active").execute()
            topics = res.data or []
            now = datetime.now(timezone.utc)

            for t in topics:
                last_checked = t.get("last_checked_at") or t.get("last_checked")
                freq = (t.get("frequency") or "daily").lower()

                is_due = False
                if not last_checked or last_checked == "Recent":
                    is_due = True
                else:
                    try:
                        last_dt = datetime.fromisoformat(last_checked.replace("Z", "+00:00"))
                        if freq == "hourly" and (now - last_dt) > timedelta(hours=1):
                            is_due = True
                        elif freq == "daily" and (now - last_dt) > timedelta(days=1):
                            is_due = True
                        elif freq == "weekly" and (now - last_dt) > timedelta(days=7):
                            is_due = True
                    except Exception:
                        is_due = False

                if is_due:
                    topic_id = t["id"]
                    user_id = t["user_id"]
                    topic_name = t["topic"]
                    print(f"[SurveillanceScheduler] Running scheduled sweep for: '{topic_name}' ({freq})", flush=True)

                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: monitor_service.check_topic_updates(topic=topic_name, user_id=user_id, topic_id=topic_id)
                    )

                    admin.table("watchlist_topics").update({
                        "last_checked_at": now.isoformat()
                    }).eq("id", topic_id).execute()

        except Exception as e:
            # Back off quietly if table is not yet migrated in Supabase
            print(f"[SurveillanceScheduler] Sweep loop note: {e}", flush=True)
            await asyncio.sleep(300)
            continue

        await asyncio.sleep(60)
