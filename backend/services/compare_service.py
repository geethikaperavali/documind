import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.database import get_supabase_admin
from backend.services.gemini_gateway import gemini_gateway
from backend.services.temporal_intelligence import temporal_service
from backend.services.search_service import search_service

class CompareService:
    """
    DocuMind Compare & Verify Engine.
    Executes deep comparison between:
    1. Document vs. Document (clause differences, conflicts, omissions, terms).
    2. Document vs. Current Live Reality (identifying repealed acts, changed rules, and empirical discrepancies).
    """

    DOC_VS_DOC_PROMPT = """You are DocuMind's Senior Legal and Contract Verification Auditor.
Your task is to conduct an uncompromising, clause-by-clause comparative audit between Document A and Document B.

CRITICAL INSTRUCTIONS:
1. Identify all changed clauses, modified obligations, pricing, deadlines, and liabilities.
2. Flag conflicting claims or direct contradictions between Document A and Document B.
3. Identify missing information (sections present in Document A but omitted in Document B, and vice-versa).
4. Provide concrete evidence quoting the respective text excerpts from both documents.

Return valid JSON conforming to this schema:
{
  "comparison_summary": "High-level 2-3 paragraph overview of the changes and overall risk impact",
  "similarity_score_pct": 75,
  "key_differences_count": 5,
  "changed_clauses": [
    {
      "clause_topic": "e.g. Payment Terms / Governing Law / Confidentiality",
      "doc_a_version": "Direct excerpt or description from Doc A",
      "doc_b_version": "Direct excerpt or description from Doc B",
      "change_type": "Material Change | Moderate Modification | Scope Expansion | Restriction Added",
      "risk_level": "Low | Moderate | High",
      "analysis": "Explanation of the legal/business significance of this difference"
    }
  ],
  "contradictions_and_conflicts": [
    {
      "issue": "Contradictory claim or obligation",
      "doc_a_claim": "Claim in Doc A",
      "doc_b_claim": "Conflicting claim in Doc B",
      "recommended_resolution": "Actionable advice to resolve conflict"
    }
  ],
  "omissions": {
    "only_in_doc_a": ["Clause or term present only in Document A"],
    "only_in_doc_b": ["Clause or term present only in Document B"]
  },
  "overall_recommendation": "Executive conclusion and sign-off advice"
}
"""

    DOC_VS_WEB_PROMPT = """You are DocuMind's Senior Regulatory Compliance and Verification Officer.
Your task is to compare an uploaded document against verified, live external statutory and official information.

CRITICAL RULES:
1. Examine each key clause/claim in the document.
2. Determine if it is currently active, amended, repealed, expired, or superseded.
3. Cite authoritative evidence and explain every discovered discrepancy.
4. If a clause conforms to current law, mark it as "Aligned / Active".
5. Never invent regulations or current provisions.

Return valid JSON conforming to this schema:
{
  "audit_summary": "Comprehensive assessment of the document's alignment with current official reality",
  "overall_compliance_status": "Fully Compliant | Partially Compliant – Amendments Required | Non-Compliant – Relies on Repealed Law",
  "verified_clauses": [
    {
      "document_clause": "Quoted clause or claim from document",
      "page_number": 1,
      "current_legal_or_official_status": "Currently Active | Amended | Repealed | Expired | Superseded | Status Unverified",
      "evidence_and_discrepancy": "Detailed evidence comparing document text to present-day law or standards",
      "current_applicable_rule": "What applies today or 'No direct equivalent'",
      "risk_rating": "Low | Moderate | Critical",
      "citation": "Official source or statutory reference"
    }
  ],
  "urgent_action_items": [
    "Specific clause that must be immediately amended or updated"
  ]
}
"""

    def __init__(self):
        self.temporal_service = temporal_service
        self.search_service = search_service

    def compare_documents(
        self,
        doc_a_id: str,
        doc_b_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Compares two user documents uploaded in Knowledge Base.
        """
        admin = get_supabase_admin()
        
        # 1. Fetch document metadata
        doc_a_res = admin.table("documents").select("*").eq("id", doc_a_id).eq("user_id", user_id).execute()
        doc_b_res = admin.table("documents").select("*").eq("id", doc_b_id).eq("user_id", user_id).execute()

        if not doc_a_res.data or not doc_b_res.data:
            return {"error": "One or both documents could not be found."}

        doc_a = doc_a_res.data[0]
        doc_b = doc_b_res.data[0]

        # 2. Fetch full document chunks without artificial truncation
        chunks_a = admin.table("document_chunks").select("content, page_number").eq("document_id", doc_a_id).order("chunk_index").execute().data or []
        chunks_b = admin.table("document_chunks").select("content, page_number").eq("document_id", doc_b_id).order("chunk_index").execute().data or []

        # Aggregate comprehensive content across all chunks
        text_a = "\n\n".join([f"[Page {c.get('page_number', 1)}]: {c.get('content', '')}" for c in chunks_a])
        text_b = "\n\n".join([f"[Page {c.get('page_number', 1)}]: {c.get('content', '')}" for c in chunks_b])

        # Support full multi-page document comparison (up to 120,000 characters ~60-80 pages)
        max_doc_chars = 120000
        if len(text_a) > max_doc_chars:
            text_a = text_a[:max_doc_chars] + f"\n\n... [Note: Truncated at {max_doc_chars} chars across {len(chunks_a)} chunks]"
        if len(text_b) > max_doc_chars:
            text_b = text_b[:max_doc_chars] + f"\n\n... [Note: Truncated at {max_doc_chars} chars across {len(chunks_b)} chunks]"

        user_prompt = f"""DOCUMENT A: "{doc_a.get('name')}" (Format: {doc_a.get('file_type')}, Size: {doc_a.get('file_size')} bytes, {len(chunks_a)} chunks)
=== DOCUMENT A CONTENT ===
{text_a}

DOCUMENT B: "{doc_b.get('name')}" (Format: {doc_b.get('file_type')}, Size: {doc_b.get('file_size')} bytes, {len(chunks_b)} chunks)
=== DOCUMENT B CONTENT ===
{text_b}

Perform the rigorous comparative audit and return the strict JSON schema.
"""
        default_fallback = {
            "comparison_summary": "Document comparison could not be processed due to transient AI latency.",
            "similarity_score_pct": 50,
            "key_differences_count": 0,
            "changed_clauses": [],
            "contradictions_and_conflicts": [],
            "omissions": {"only_in_doc_a": [], "only_in_doc_b": []},
            "overall_recommendation": "Please retry comparison in a few moments."
        }

        result_dict = gemini_gateway.generate_json(
            prompt=user_prompt,
            system_instruction=self.DOC_VS_DOC_PROMPT,
            temperature=0.1,
            default_fallback=default_fallback
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        result_dict["doc_a"] = {"id": doc_a_id, "name": doc_a.get("name")}
        result_dict["doc_b"] = {"id": doc_b_id, "name": doc_b.get("name")}
        result_dict["compared_at"] = now_iso

        # 3. Persist audit to database
        try:
            admin.table("comparison_audits").insert({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "audit_type": "doc_vs_doc",
                "title": f"Comparison: {doc_a.get('name')} vs {doc_b.get('name')}",
                "doc_a_id": doc_a_id,
                "doc_b_id": doc_b_id,
                "audit_data": result_dict,
                "created_at": now_iso
            }).execute()
        except Exception as e:
            print(f"[CompareService] DB save note: {e}")

        return result_dict

    def compare_document_against_web(
        self,
        doc_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Compares an uploaded document against current official web information across full document scope.
        """
        admin = get_supabase_admin()
        doc_res = admin.table("documents").select("*").eq("id", doc_id).eq("user_id", user_id).execute()
        if not doc_res.data:
            return {"error": "Document not found."}

        doc = doc_res.data[0]
        chunks = admin.table("document_chunks").select("content, page_number").eq("document_id", doc_id).order("chunk_index").execute().data or []
        doc_text = "\n\n".join([f"[Page {c.get('page_number', 1)}]: {c.get('content', '')}" for c in chunks])

        # Support full document analysis (up to 100,000 characters)
        max_chars = 100000
        if len(doc_text) > max_chars:
            doc_text = doc_text[:max_chars] + f"\n\n... [Note: Truncated at {max_chars} chars across {len(chunks)} chunks]"

        # 1. Search web for authoritative updates matching document content
        sample_query = f"{doc.get('name', '')} governing act current law amendments latest regulations"
        web_sources = self.search_service.search(sample_query, max_results=5, prefer_official=True)
        sources_summary = "\n".join([f"- {s['title']} ({s['category']}): {s['snippet']} [URL: {s['url']}]" for s in web_sources])

        now_iso = datetime.now(timezone.utc).isoformat()
        user_prompt = f"""DOCUMENT TO VERIFY: "{doc.get('name')}" ({len(chunks)} chunks, Format: {doc.get('file_type')})
=== EXTRACTED DOCUMENT TEXT ===
{doc_text}

=== VERIFIED LIVE OFFICIAL WEB SOURCES RETRIEVED AT {now_iso} ===
{sources_summary if sources_summary else "No external web results. Evaluate based on known active statutory provisions."}

Conduct a clause-by-clause reality check and identify all outdated provisions, changed thresholds, or superseded requirements across the entire document.
Return JSON matching DOC_VS_WEB_PROMPT.
"""
        default_fallback = {
            "audit_summary": "Verification against live web could not be processed due to API latency.",
            "overall_compliance_status": "Partially Compliant – Amendments Required",
            "verified_clauses": [],
            "urgent_action_items": []
        }

        result_dict = gemini_gateway.generate_json(
            prompt=user_prompt,
            system_instruction=self.DOC_VS_WEB_PROMPT,
            temperature=0.1,
            default_fallback=default_fallback
        )

        result_dict["document"] = {"id": doc_id, "name": doc.get("name")}
        result_dict["verified_at"] = now_iso
        result_dict["external_sources"] = web_sources

        # 2. Persist audit to database
        try:
            admin.table("comparison_audits").insert({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "audit_type": "doc_vs_web",
                "title": f"Live Reality Audit: {doc.get('name')}",
                "doc_a_id": doc_id,
                "doc_b_id": None,
                "audit_data": result_dict,
                "created_at": now_iso
            }).execute()
        except Exception as e:
            print(f"[CompareService] DB save note: {e}")

        return result_dict

compare_service = CompareService()
