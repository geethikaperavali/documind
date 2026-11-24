import re
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.services.gemini_gateway import gemini_gateway
from backend.services.search_service import search_service
from backend.database import get_supabase_admin

class TemporalIntelligence:
    """
    DocuMind Temporal Intelligence Engine.
    Evaluates whether legal, regulatory, or policy statements are:
    - Currently Active
    - Amended
    - Repealed / Overruled
    - Expired
    - Superseded
    - Not Yet Effective / Upcoming
    """

    TEMPORAL_SYSTEM_PROMPT = """You are DocuMind's Senior Regulatory and Temporal Intelligence Analyst.
Your job is to determine the exact, present-day real-world status of a law, section, scheme, regulation, threshold, or policy.

CRITICAL RULES:
1. Always evaluate against the current calendar year.
2. If a statute or act was repealed, superseded, or codified into a newer act (e.g., IPC/CrPC/IEA superseded by BNS/BNSS/BSA in India, or EU AI Act provisions rolling out, or US regulatory shifts), clearly explain what replaced it and the effective date.
3. Categorize the status strictly as ONE of:
   - "Currently Active"
   - "Amended"
   - "Repealed"
   - "Expired"
   - "Superseded"
   - "Not Yet Effective"
   - "Upcoming"
   - "Status Unverified"
4. Distinguish between what the historical text was and what applies today.
5. If the provision is actively valid without amendments, confirm it is active.

Return valid JSON conforming to this schema:
{
  "temporal_detected": true,
  "subject": "e.g. IPC Section 377 / IT Act Section 66A / 401(k) limit / Maternity Benefit Act",
  "jurisdiction": "e.g. India, United States, European Union, Global",
  "status_classification": "Currently Active | Amended | Repealed | Expired | Superseded | Not Yet Effective | Upcoming | Status Unverified",
  "historical_position": "What was the previous rule or original text",
  "current_position": "What is the exact valid law or rule today",
  "what_changed": "Key amendments, supreme court judgments, gazette notifications, or superseding acts",
  "effective_date": "Date the change took effect (e.g. July 1, 2024 / September 6, 2018)",
  "current_applicable_provision": "The active section or governing act today (e.g. BNS Section X / Active)",
  "risk_assessment": "Low | Moderate | High | Critical (if relying on repealed provision)",
  "executive_summary": "1-2 sentence executive briefing on current status"
}
"""

    TEMPORAL_TRIGGER_PATTERNS = [
        r'\bsection\s+\d+[a-z]?\b',
        r'\barticle\s+\d+[a-z]?\b',
        r'\bact\s*,?\s*\d{4}\b',
        r'\brules\s*,?\s*\d{4}\b',
        r'\bcircular\s*(?:no\.?)?\s*[\w\/-]+\b',
        r'\bgazette\b',
        r'\bnotification\b',
        r'\bbns\b|\bbharatiya\s+nyaya\b|\bipc\b|\bcrpc\b',
        r'\bgdpr\b|\bhipaa\b|\bdpdp\b|\beu\s+ai\s+act\b',
        r'\brepeal(?:ed|s)?\b|\bamend(?:ed|ment)?\b|\bsuperseded?\b'
    ]

    def __init__(self):
        self.search_service = search_service

    def is_time_sensitive(self, text: str) -> bool:
        """
        Determines whether a query or clause likely involves time-sensitive legal/regulatory status.
        """
        text_lower = text.lower()
        temporal_clues = [
            "is this still valid", "is this repealed", "amendment", "current law",
            "what changed", "effective date", "new act", "superseded", "ipc vs bns",
            "latest rule", "valid today", "overruled", "sunset date"
        ]
        if any(clue in text_lower for clue in temporal_clues):
            return True

        for pat in self.TEMPORAL_TRIGGER_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return True

        return False

    def verify_temporal_status(
        self,
        query: str,
        historical_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Conducts end-to-end temporal verification against live authoritative sources.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Search authoritative sources
        search_query = f"{query} current legal status repealed amended effective date latest notification"
        external_sources = self.search_service.search(
            query=search_query,
            max_results=5,
            prefer_official=True
        )

        sources_text = "\n".join([
            f"- [{s['domain']} | {s['published_date']}]: {s['title']}\n  Snippet: {s['snippet']}\n  URL: {s['url']}"
            for s in external_sources
        ])

        user_prompt = f"""EVALUATE TEMPORAL STATUS:
Query / Provision to verify: "{query}"
Historical Context from User/Document: "{historical_context or 'Not specified'}"
Current Verification Timestamp: {now_iso}

LIVE EXTERNAL SEARCH FINDINGS:
{sources_text if sources_text else "No external search hits returned. Use verified legal corpus."}

Analyze whether this provision is currently active, amended, repealed, expired, or superseded.
Return strict JSON matching TEMPORAL_SYSTEM_PROMPT.
"""
        default_fallback = {
            "temporal_detected": True,
            "subject": query,
            "jurisdiction": "Unspecified",
            "status_classification": "Status Unverified",
            "historical_position": historical_context or "Not established",
            "current_position": "Could not verify real-time status due to AI connectivity timeout.",
            "what_changed": "Verification pending live source retrieval.",
            "effective_date": "Unknown",
            "current_applicable_provision": "Status Unverified",
            "risk_assessment": "Moderate",
            "executive_summary": "Temporal verification could not be completed at this time."
        }

        analysis_dict = gemini_gateway.generate_json(
            prompt=user_prompt,
            system_instruction=self.TEMPORAL_SYSTEM_PROMPT,
            temperature=0.1,
            default_fallback=default_fallback
        )

        # 3. Assemble complete 7-part standardized temporal response
        result = {
            "subject": analysis_dict.get("subject", query),
            "jurisdiction": analysis_dict.get("jurisdiction", "General"),
            "status_classification": analysis_dict.get("status_classification", "Status Unverified"),
            "risk_assessment": analysis_dict.get("risk_assessment", "Moderate"),
            "historical_position": analysis_dict.get("historical_position", "Historical context not established"),
            "current_position": analysis_dict.get("current_position", "Current position unverified"),
            "what_changed": analysis_dict.get("what_changed", "No amendments noted"),
            "effective_date": analysis_dict.get("effective_date", "Date not verified"),
            "current_applicable_provision": analysis_dict.get("current_applicable_provision", "Status Unverified"),
            "executive_summary": analysis_dict.get("executive_summary", "Temporal check completed."),
            "verified_at": now_iso,
            "official_sources": [
                {
                    "title": s["title"],
                    "url": s["url"],
                    "domain": s["domain"],
                    "published_date": s["published_date"],
                    "badge": s["category"]
                }
                for s in external_sources
            ]
        }

        return result

    def audit_document_temporality(
        self,
        document_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Scans all chunks of an uploaded document for temporal triggers,
        verifying identified clauses in parallel to construct a Temporal Health Scorecard.
        """
        admin = get_supabase_admin()

        # 1. Fetch document metadata and chunks
        doc_res = admin.table("documents").select("name").eq("id", document_id).eq("user_id", user_id).execute()
        if not doc_res.data:
            return {"error": "Document not found"}

        doc_name = doc_res.data[0]["name"]
        chunks = admin.table("document_chunks") \
            .select("content, page_number, chunk_index") \
            .eq("document_id", document_id) \
            .order("chunk_index") \
            .execute().data or []

        findings = []
        status_counts = {
            "Currently Active": 0,
            "Amended": 0,
            "Repealed": 0,
            "Expired": 0,
            "Superseded": 0,
            "Not Yet Effective": 0,
            "Upcoming": 0,
            "Status Unverified": 0
        }

        # 2. Extract unique triggers
        triggers_to_verify = []
        seen_terms = set()

        for c in chunks:
            text = c.get("content", "")
            page = c.get("page_number", 1)

            for pat in self.TEMPORAL_TRIGGER_PATTERNS:
                matches = re.finditer(pat, text, re.IGNORECASE)
                for m in matches:
                    trigger_term = m.group(0).strip().lower()
                    if trigger_term not in seen_terms and len(triggers_to_verify) < 5:
                        seen_terms.add(trigger_term)
                        triggers_to_verify.append({
                            "term": trigger_term,
                            "page": page,
                            "context": f"Mentioned in '{doc_name}' on Page {page}: ...{text[:200]}...",
                            "excerpt": text[:180] + ("..." if len(text) > 180 else "")
                        })

        # 3. Verify triggers concurrently
        def verify_single_trigger(item):
            verdict = self.verify_temporal_status(
                query=item["term"],
                historical_context=item["context"]
            )
            verdict["page_number"] = item["page"]
            verdict["excerpt"] = item["excerpt"]
            return verdict

        if triggers_to_verify:
            with ThreadPoolExecutor(max_workers=min(5, len(triggers_to_verify))) as executor:
                findings = list(executor.map(verify_single_trigger, triggers_to_verify))

            for verdict in findings:
                st = verdict.get("status_classification", "Status Unverified")
                status_counts[st] = status_counts.get(st, 0) + 1

        # 4. Overall document risk assessment
        high_risk_count = status_counts.get("Repealed", 0) + status_counts.get("Expired", 0) + status_counts.get("Superseded", 0)
        moderate_risk_count = status_counts.get("Amended", 0)

        if high_risk_count > 0:
            doc_risk = "HIGH RISK – Document relies on repealed, expired, or superseded provisions."
            risk_badge = "high"
        elif moderate_risk_count > 0:
            doc_risk = "MODERATE RISK – Document contains amended provisions that require verification."
            risk_badge = "moderate"
        elif len(findings) == 0:
            doc_risk = "NO TEMPORAL CONCERNS DETECTED – Content contains standard operational or non-statutory material."
            risk_badge = "low"
        else:
            doc_risk = "LOW RISK – Document provisions appear aligned with active standards."
            risk_badge = "low"

        return {
            "document_id": document_id,
            "document_name": doc_name,
            "overall_temporal_risk": doc_risk,
            "risk_badge": risk_badge,
            "status_breakdown": status_counts,
            "clauses_audited_count": len(findings),
            "findings": findings,
            "audited_at": datetime.now(timezone.utc).isoformat()
        }

temporal_service = TemporalIntelligence()
