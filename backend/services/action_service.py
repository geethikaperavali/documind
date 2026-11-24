import uuid
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.database import get_supabase_admin
from backend.services.gemini_gateway import gemini_gateway

class ActionService:
    """
    DocuMind Action Studio Engine.
    Converts research dossiers, document intelligence, and temporal findings into:
    1. Implementation Plans (milestones, dependencies, owners)
    2. Task Breakdowns (WBS action items)
    3. Checklists (interactive verification items with pass/fail)
    4. Business & Risk Analysis (SWOT, risk mitigation, feasibility)
    5. Executive Reports (decision briefs)
    6. Study Material (flashcards, concept summaries, FAQs)
    """

    ACTION_SYSTEM_PROMPT = """You are DocuMind's Principal Operations Strategist and Action Architect.
Your task is to transform dense document text or research dossiers into a high-impact, directly actionable decision artifact.

ARTIFACT TYPES:
1. "plan": Implementation Plan (Phased timeline, key milestones, dependencies, critical paths)
2. "tasks": Task Breakdown (WBS tasks, deliverables, estimated effort, responsibility matrix)
3. "checklist": Compliance & Action Checklist (Step-by-step verification checks with pass/fail criteria and statutory citations)
4. "business_analysis": Strategic & Risk Analysis (SWOT matrix, operational risk assessment, financial impact, ROI)
5. "report": Executive Decision Report (Briefing, strategic options, trade-offs, final recommendation)
6. "study": Study & Training Material (Core concepts, Q&A flashcards, key definitions, exam/review highlights)

STRICT FORMATTING RULE:
Return valid JSON matching this schema:
{
  "artifact_type": "plan | tasks | checklist | business_analysis | report | study",
  "title": "Clear Action-Oriented Title",
  "executive_summary": "1-2 paragraphs contextualizing the operational goal",
  "sections": [
    {
      "heading": "Phase 1 / Key Factor / Category",
      "description": "Overview of this section",
      "items": [
        {
          "name": "Actionable item title",
          "details": "Specific actionable steps, citation, or metric",
          "priority": "High | Medium | Low",
          "status": "pending"
        }
      ]
    }
  ],
  "deliverables": [
    "Concrete output 1",
    "Concrete output 2"
  ],
  "governing_rules_or_citations": [
    "Referenced statute, document clause, or standard"
  ]
}
"""

    def generate_action_artifact(
        self,
        artifact_type: str,
        source_type: str,
        source_id: Optional[str],
        user_id: str,
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates structured actionable artifact from a document or research report and persists it.
        """
        admin = get_supabase_admin()
        source_title = "Workspace Knowledge"
        source_content = ""

        # 1. Fetch source content
        if source_type == "document" and source_id:
            try:
                doc_res = admin.table("documents").select("name").eq("id", source_id).eq("user_id", user_id).execute()
                if doc_res.data:
                    source_title = doc_res.data[0]["name"]
                
                chunks = admin.table("document_chunks").select("content, page_number").eq("document_id", source_id).order("chunk_index").limit(12).execute().data or []
                source_content = "\n\n".join([f"[Page {c.get('page_number', 1)}]: {c.get('content', '')}" for c in chunks])
            except Exception as e:
                print(f"[ActionService] Document fetch warning: {e}")

        elif source_type == "research" and source_id:
            try:
                rep_res = admin.table("research_reports").select("*").eq("id", source_id).eq("user_id", user_id).execute()
                if rep_res.data:
                    rep = rep_res.data[0]
                    source_title = rep.get("title", "Research Report")
                    r_data = rep.get("report_data", {})
                    source_content = f"TOPIC: {r_data.get('topic')}\nSUMMARY: {r_data.get('executive_summary')}\nFINDINGS: {json.dumps(r_data.get('key_findings'))}\nREGULATIONS: {r_data.get('policy_and_regulatory_framework')}"
            except Exception as e:
                print(f"[ActionService] Research report fetch warning: {e}")
                source_content = "Research dossier data."

        if not source_content:
            source_content = custom_instructions or "Transform user workspace context into an action plan."

        # 2. Invoke Gemini via gateway
        user_prompt = f"""GENERATE ACTION ARTIFACT:
Type requested: "{artifact_type}"
Source: "{source_title}"
Additional User Guidance: "{custom_instructions or 'Provide comprehensive actionable breakdown.'}"

=== SOURCE MATERIAL ===
{source_content[:8000]}

Generate structured JSON matching ACTION_SYSTEM_PROMPT.
"""
        default_fallback = {
            "artifact_type": artifact_type,
            "title": f"Action Plan: {source_title}",
            "executive_summary": "Action artifact generation completed.",
            "sections": [
                {
                    "heading": "Phase 1: Immediate Action Items",
                    "description": "Essential initial tasks",
                    "items": [
                        {"name": "Review source document stipulations", "details": "Verify scope and timeline", "priority": "High", "status": "pending"}
                    ]
                }
            ],
            "deliverables": ["Action Roadmap"],
            "governing_rules_or_citations": [source_title]
        }

        artifact_json = gemini_gateway.generate_json(
            prompt=user_prompt,
            system_instruction=self.ACTION_SYSTEM_PROMPT,
            temperature=0.2,
            default_fallback=default_fallback
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        artifact_id = str(uuid.uuid4())
        title = artifact_json.get("title") or f"Action Plan: {source_title}"

        artifact_json["id"] = artifact_id
        artifact_json["created_at"] = now_iso
        artifact_json["source_title"] = source_title
        artifact_json["user_id"] = user_id
        artifact_json["title"] = title
        artifact_json["artifact_type"] = artifact_type

        if not hasattr(self, "_memory_artifacts"):
            self._memory_artifacts = {}
        self._memory_artifacts[artifact_id] = artifact_json

        # 3. Persist to action_artifacts table
        try:
            admin.table("action_artifacts").insert({
                "id": artifact_id,
                "user_id": user_id,
                "artifact_type": artifact_type,
                "title": title,
                "source_title": source_title,
                "artifact_data": artifact_json,
                "created_at": now_iso
            }).execute()
        except Exception as e:
            print(f"[ActionService] DB save note: {e}")

        return artifact_json

    def list_artifacts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Lists all saved action artifacts for the authenticated user with memory fallback.
        """
        try:
            admin = get_supabase_admin()
            res = admin.table("action_artifacts") \
                .select("id, artifact_type, title, source_title, created_at") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .execute()
            if res.data:
                return res.data
        except Exception as e:
            pass

        if not hasattr(self, "_memory_artifacts"):
            self._memory_artifacts = {}
        items = []
        for art in sorted(self._memory_artifacts.values(), key=lambda a: a.get("created_at", ""), reverse=True):
            if art.get("user_id") == user_id or not user_id:
                items.append({
                    "id": art.get("id"),
                    "artifact_type": art.get("artifact_type", "plan"),
                    "title": art.get("title"),
                    "source_title": art.get("source_title"),
                    "created_at": art.get("created_at")
                })
        return items

    def get_artifact(self, artifact_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific action artifact by ID with memory fallback.
        """
        try:
            admin = get_supabase_admin()
            res = admin.table("action_artifacts") \
                .select("*") \
                .eq("id", artifact_id) \
                .eq("user_id", user_id) \
                .execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                data = row.get("artifact_data", {})
                data["id"] = row.get("id")
                data["title"] = row.get("title")
                data["artifact_type"] = row.get("artifact_type")
                data["source_title"] = row.get("source_title")
                data["created_at"] = row.get("created_at")
                return data
        except Exception:
            pass

        if hasattr(self, "_memory_artifacts") and artifact_id in self._memory_artifacts:
            art = self._memory_artifacts[artifact_id]
            if art.get("user_id") == user_id or not user_id:
                return art
        return None

    def update_artifact(
        self,
        artifact_id: str,
        user_id: str,
        title: Optional[str] = None,
        artifact_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Updates an existing action artifact with memory fallback.
        """
        if hasattr(self, "_memory_artifacts") and artifact_id in self._memory_artifacts:
            if title:
                self._memory_artifacts[artifact_id]["title"] = title
            if artifact_data:
                self._memory_artifacts[artifact_id].update(artifact_data)

        try:
            admin = get_supabase_admin()
            update_payload = {}
            if title:
                update_payload["title"] = title
            if artifact_data:
                update_payload["artifact_data"] = artifact_data

            if not update_payload:
                return self.get_artifact(artifact_id, user_id)

            res = admin.table("action_artifacts") \
                .update(update_payload) \
                .eq("id", artifact_id) \
                .eq("user_id", user_id) \
                .execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            pass

        return self.get_artifact(artifact_id, user_id)

    def delete_artifact(self, artifact_id: str, user_id: str) -> bool:
        """
        Permanently deletes an action artifact with memory fallback.
        """
        if hasattr(self, "_memory_artifacts"):
            self._memory_artifacts.pop(artifact_id, None)

        try:
            admin = get_supabase_admin()
            admin.table("action_artifacts") \
                .delete() \
                .eq("id", artifact_id) \
                .eq("user_id", user_id) \
                .execute()
            return True
        except Exception as e:
            pass
        return True

action_service = ActionService()
