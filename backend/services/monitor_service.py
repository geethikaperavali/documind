import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.database import get_supabase_admin
from backend.services.gemini_gateway import gemini_gateway
from backend.services.search_service import search_service

class MonitorService:
    """
    DocuMind Live Monitor Engine.
    Tracks user watchlists, periodically monitors external sources,
    detects delta changes and critical policy/market shifts.
    """

    MONITOR_ANALYSIS_PROMPT = """You are DocuMind's Real-Time Regulatory & Market Monitor.
Your task is to analyze newly retrieved live web results for a tracked topic and detect meaningful updates, changes, or alerts.

EVALUATION CRITERIA:
1. "change_level": "None" (No material news) | "Routine Update" (Ongoing progress) | "Significant Shift" (New gazette, amendment, ruling, policy, or market disruption)
2. Summarize what is genuinely new or changed compared to general background knowledge.
3. Highlight official notifications, dates, and direct citations.

Return valid JSON:
{
  "change_level": "None | Routine Update | Significant Shift",
  "headline": "Punchy 1-sentence update headline",
  "change_summary": "2-3 paragraphs describing the verified latest developments",
  "action_required": true,
  "recommended_actions": [
    "Specific step or compliance verification recommended"
  ]
}
"""

    def __init__(self):
        self.search_service = search_service

    def check_topic_updates(
        self,
        topic: str,
        user_id: str,
        topic_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a live external source sweep for a tracked topic and detects updates.
        """
        check_time = datetime.now(timezone.utc).isoformat()

        # 1. Search live web sources
        query = f"{topic} latest official update notification announcement news 2024 2025"
        live_sources = self.search_service.search(query, max_results=5, prefer_official=True)

        sources_text = "\n".join([f"- [{s['domain']} | {s['published_date']}]: {s['title']}\n  Snippet: {s['snippet']}\n  URL: {s['url']}" for s in live_sources])

        # 2. Invoke Gemini via gateway
        user_prompt = f"""TRACKED TOPIC: "{topic}"
CHECK TIMESTAMP: {check_time}

=== RECENTLY RETRIEVED SOURCES ===
{sources_text if sources_text else "No recent external sources found."}

Analyze whether there are meaningful new developments, policy amendments, or market changes.
Return strict JSON matching MONITOR_ANALYSIS_PROMPT.
"""
        default_fallback = {
            "change_level": "Routine Update",
            "headline": f"Recent coverage monitored for {topic}",
            "change_summary": "Monitoring sweep completed. Sources reviewed and active.",
            "action_required": False,
            "recommended_actions": ["Continue periodic surveillance."]
        }

        update_info = gemini_gateway.generate_json(
            prompt=user_prompt,
            system_instruction=self.MONITOR_ANALYSIS_PROMPT,
            temperature=0.1,
            default_fallback=default_fallback
        )

        result = {
            "topic_id": topic_id,
            "topic": topic,
            "checked_at": check_time,
            "change_level": update_info.get("change_level", "None"),
            "headline": update_info.get("headline", ""),
            "summary": update_info.get("change_summary", ""),
            "action_required": update_info.get("action_required", False),
            "recommended_actions": update_info.get("recommended_actions", []),
            "sources": live_sources,
            "sources_count": len(live_sources)
        }

        # 3. Save monitor log in database if possible
        try:
            admin = get_supabase_admin()
            admin.table("monitor_logs").insert({
                "user_id": user_id,
                "topic": topic,
                "change_level": result["change_level"],
                "headline": result["headline"],
                "log_data": result,
                "created_at": check_time
            }).execute()
        except Exception:
            pass

        return result

monitor_service = MonitorService()
