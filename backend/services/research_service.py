"""
DocuMind Universal Research Studio Engine.
Executes multi-query investigations across live web sources, official registries,
government portals, and industry data across 12+ professional domains.
Synthesizes structured research dossiers with clickable citations, source provenance registries,
and specialized AI industry intelligence.
"""

import uuid
import json
import concurrent.futures
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.services.gemini_gateway import gemini_gateway
from backend.config import settings
from backend.services.search_service import search_service
from backend.services.source_registry import source_registry
from backend.services.temporal_intelligence import temporal_service
from backend.services.ai_intelligence import ai_intelligence_service
from backend.database import get_supabase_admin

class ResearchService:
    """
    DocuMind Universal Research Studio Engine.
    Delivers deep intelligence dossiers across AI/ML, Law, Finance, Healthcare,
    Public Policy, Academics, Cybersecurity, and Engineering.
    """

    RESEARCH_SYSTEM_PROMPT = """You are DocuMind's Senior Research Scientist and Intelligence Analyst.
Your task is to compile a rigorous, comprehensive, highly structured research dossier based on verified sources and empirical evidence.

STRICT RESEARCH & EDITORIAL STANDARDS:
1. Grounding & Evidence: Every factual external claim must be traceable to the retrieved sources. Never invent statistics, benchmarks, financial metrics, government schemes, or dates.
2. Authority Differentiation: Explicitly distinguish official primary directives (statutes, gazettes, direct vendor docs) from secondary commentary or analyst opinions.
3. For AI & Technology inquiries: Clearly distinguish vendor-reported claims from independent evaluations (e.g., LMSYS Chatbot Arena Elo, SWE-bench Verified). Detail context windows, API token pricing, and deprecation lifecycles.
4. Structure: You must provide a structured report with:
   - Executive Brief & Core Takeaways
   - Technical, Statutory or Regulatory Framework
   - Market, Economic or Industry Dynamics
   - Emerging Risks, Uncertainties & Vulnerabilities
   - Strategic & Actionable Implications
5. Citations: Cite sources in-text using format [Source X: Domain, Date].
6. Output format: Return strictly valid JSON matching this schema:
{
  "title": "Concise, descriptive report title",
  "topic": "Normalized topic keyword",
  "domain_classified": "ai_ml | law_regulation | finance_markets | healthcare_medicine | gov_policy | academic_research | software_cybersecurity | general_universal",
  "executive_summary": "High-level 2-3 paragraph strategic summary",
  "key_findings": [
    "Finding 1 with [Source X: Domain, Date]",
    "Finding 2 with [Source Y: Domain, Date]"
  ],
  "policy_and_regulatory_framework": "Detailed analysis of governing laws, policies, specifications, or architectural frameworks",
  "market_and_industry_dynamics": "Commercial, operational, or industry impact, benchmark metrics, or empirical data",
  "uncertainties_and_risks": "Unresolved questions, controversies, deprecations, or emerging risks",
  "strategic_implications": "Key lessons, recommendations, or operational impact",
  "temporal_flags": [
    {
      "provision_or_policy": "Name of policy, law, or model version",
      "status": "Currently Active | Amended | Repealed | Expired | Superseded | Deprecated",
      "note": "Brief explanation"
    }
  ]
}
"""

    def __init__(self):
        self.search_service = search_service
        self.registry = source_registry
        self.temporal_service = temporal_service
        self.ai_service = ai_intelligence_service

    def conduct_research(
        self,
        topic: str,
        user_id: str,
        domain: str = "general_universal",
        depth: str = "comprehensive", # "brief", "comprehensive", "regulatory"
        save_report: bool = True
    ) -> Dict[str, Any]:
        """
        Executes an in-depth universal research investigation:
        1. Classifies if query touches AI industry intelligence.
        2. Formulates domain-specialized search queries.
        3. Retrieves authoritative sources and enriches with Source Registry metadata.
        4. Evaluates source quality and single-provider bias.
        5. Generates structured intelligence report via Gemini.
        6. Injects AI Model Comparison Matrix if AI-related.
        7. Persists report into database with safe local fallback.
        """
        retrieval_timestamp = datetime.now(timezone.utc).isoformat()
        is_ai_query = self.ai_service.is_ai_industry_query(topic) or domain == "ai_ml"

        # 1. Formulate targeted search queries
        queries = [
            f"{topic} overview authoritative analysis",
            f"{topic} latest developments 2024 2025 updates",
            f"{topic} official documentation status specifications"
        ]
        if is_ai_query:
            queries.extend([
                f"{topic} benchmark evaluation swe-bench lmsys arena",
                f"{topic} api pricing token context window release notes"
            ])
        elif domain == "law_regulation" or depth == "regulatory":
            queries.extend([
                f"{topic} gazette act law statutory compliance amendments",
                f"{topic} judicial rulings legal effective date"
            ])
        elif domain == "finance_markets":
            queries.extend([
                f"{topic} quarterly earnings regulatory filing sec balance sheet",
                f"{topic} macroeconomic impact central bank guidance"
            ])
        elif domain == "healthcare_medicine":
            queries.extend([
                f"{topic} clinical trial fda approval pubmed study",
                f"{topic} guidelines who efficacy safety"
            ])
        else:
            if depth == "comprehensive":
                queries.append(f"{topic} market analysis statistics forecast risks")

        # 2. Gather sources concurrently across targeted queries
        target_queries = queries[: 5 if depth == "comprehensive" else 2]
        all_sub_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(target_queries), 5)) as executor:
            future_to_query = {
                executor.submit(self.search_service.search, q, domain, 4, True): q
                for q in target_queries
            }
            for future in concurrent.futures.as_completed(future_to_query):
                try:
                    res = future.result()
                    all_sub_results.extend(res)
                except Exception as e:
                    print(f"[ResearchService] Sub-query error: {e}")

        seen_urls = set()
        all_sources = []
        for r in all_sub_results:
            clean_url = r["url"].rstrip("/")
            if clean_url not in seen_urls:
                seen_urls.add(clean_url)
                all_sources.append(r)

        # 3. Compile sources text for synthesis
        sources_text = ""
        structured_sources = []
        for i, s in enumerate(all_sources[:12], 1):
            auth_badge = s.get("badge", "web").upper()
            rel_level = s.get("level", "tier_3_general")
            sources_text += f"[Source {i}: {s['domain']} | {s['published_date']} | Tier: {rel_level} | Badge: {auth_badge}]\n"
            sources_text += f"Title: {s['title']}\nURL: {s['url']}\nSnippet: {s['snippet']}\n\n"
            
            structured_sources.append({
                "source_id": i,
                "title": s["title"],
                "url": s["url"],
                "domain": s["domain"],
                "source_name": s.get("source_name", s["domain"]),
                "category": s["category"],
                "level": s["level"],
                "badge": s["badge"],
                "is_official": s["is_official"],
                "freshness": s.get("freshness", "unknown"),
                "verification_criteria": s.get("verification_criteria", "Standard web index"),
                "published_date": s["published_date"],
                "retrieved_at": s["retrieved_at"]
            })

        # 4. Source Quality & Provenance Audit
        quality_audit = self.registry.evaluate_source_quality(structured_sources)

        # 5. Dedicated AI Model Intelligence (if applicable)
        ai_matrix = None
        if is_ai_query:
            try:
                ai_matrix = self.ai_service.generate_model_comparison_matrix(
                    query=topic,
                    live_web_context=sources_text[:2500]
                )
            except Exception as e:
                print(f"[ResearchService] AI Intelligence error: {e}")

        # 6. Invoke Gemini for synthesis
        user_prompt = f"""UNIVERSAL RESEARCH INVESTIGATION:
Topic: "{topic}"
Domain Focus: {domain}
Depth: {depth}
Is AI/ML Inquired: {is_ai_query}

AUTHORITATIVE SOURCES RETRIEVED AT {retrieval_timestamp}:
{sources_text if sources_text else "No external search results retrieved. Provide verified structured analysis."}

Generate the comprehensive research dossier in the required JSON schema.
"""
        default_fallback = {
            "title": f"Research Report: {topic}",
            "topic": topic,
            "domain_classified": domain,
            "executive_summary": "Comprehensive analysis could not be generated due to transient AI latency.",
            "key_findings": ["Live source retrieval completed; synthesis pending."],
            "policy_and_regulatory_framework": "Consult primary official sources for latest statutory or technical specifications.",
            "market_and_industry_dynamics": "Empirical data reflects active ongoing development.",
            "uncertainties_and_risks": "Verify specific jurisdictional or deployment guidelines before operational implementation.",
            "strategic_implications": "Review official changelogs for active compliance and release dates.",
            "temporal_flags": []
        }

        report_json = gemini_gateway.generate_json(
            prompt=user_prompt,
            system_instruction=self.RESEARCH_SYSTEM_PROMPT,
            temperature=0.2,
            default_fallback=default_fallback
        )

        # 7. Assemble complete response
        report_data = {
            "title": report_json.get("title", f"Research Report: {topic}"),
            "topic": topic,
            "domain": domain,
            "domain_label": self.registry.DOMAINS.get(domain, domain.replace("_", " ").title()),
            "depth": depth,
            "is_ai_industry_topic": is_ai_query,
            "executive_summary": report_json.get("executive_summary", ""),
            "key_findings": report_json.get("key_findings", []),
            "policy_and_regulatory_framework": report_json.get("policy_and_regulatory_framework", ""),
            "market_and_industry_dynamics": report_json.get("market_and_industry_dynamics", ""),
            "uncertainties_and_risks": report_json.get("uncertainties_and_risks", ""),
            "strategic_implications": report_json.get("strategic_implications", ""),
            "temporal_flags": report_json.get("temporal_flags", []),
            "sources": structured_sources,
            "source_quality_audit": quality_audit,
            "ai_intelligence_matrix": ai_matrix,
            "total_sources": len(structured_sources),
            "official_sources_count": sum(1 for s in structured_sources if s.get("is_official")),
            "created_at": retrieval_timestamp
        }

        # 8. Save report in Supabase (with safe memory fallback)
        report_id = str(uuid.uuid4())
        report_data["id"] = report_id
        report_data["user_id"] = user_id

        if not hasattr(self, "_memory_reports"):
            self._memory_reports = {}
        self._memory_reports[report_id] = report_data

        if save_report and user_id:
            try:
                admin = get_supabase_admin()
                admin.table("research_reports").insert({
                    "id": report_id,
                    "user_id": user_id,
                    "title": report_data["title"],
                    "topic": topic,
                    "depth": depth,
                    "report_data": report_data,
                    "created_at": retrieval_timestamp
                }).execute()
            except Exception as e:
                print(f"[ResearchService] DB save note (safe fallback): {e}")

        return report_data

    def list_saved_reports(self, user_id: str, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves user's saved research dossiers from database with memory fallback.
        """
        try:
            admin = get_supabase_admin()
            q = admin.table("research_reports").select("id, title, topic, depth, created_at").eq("user_id", user_id)
            if search_query and search_query.strip():
                q = q.ilike("title", f"%{search_query.strip()}%")
            res = q.order("created_at", desc=True).execute()
            if res.data:
                return res.data
        except Exception:
            pass

        # Memory store fallback
        if not hasattr(self, "_memory_reports"):
            self._memory_reports = {}

        results = []
        for rep in sorted(self._memory_reports.values(), key=lambda r: r.get("created_at", ""), reverse=True):
            if rep.get("user_id") == user_id or not user_id:
                if search_query and search_query.strip():
                    if search_query.lower() not in rep.get("title", "").lower() and search_query.lower() not in rep.get("topic", "").lower():
                        continue
                results.append({
                    "id": rep.get("id"),
                    "title": rep.get("title"),
                    "topic": rep.get("topic"),
                    "depth": rep.get("depth", "comprehensive"),
                    "domain": rep.get("domain", "general_universal"),
                    "domain_label": rep.get("domain_label", "Universal"),
                    "total_sources": rep.get("total_sources", 0),
                    "source_quality_audit": rep.get("source_quality_audit", {}),
                    "created_at": rep.get("created_at")
                })
        return results

    def get_saved_report(self, report_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific research report by ID with memory fallback.
        """
        try:
            admin = get_supabase_admin()
            res = admin.table("research_reports").select("*").eq("id", report_id).eq("user_id", user_id).execute()
            if res.data:
                row = res.data[0]
                data = row.get("report_data", {})
                data["id"] = row.get("id")
                data["created_at"] = row.get("created_at")
                return data
        except Exception:
            pass

        if hasattr(self, "_memory_reports") and report_id in self._memory_reports:
            rep = self._memory_reports[report_id]
            if rep.get("user_id") == user_id or not user_id:
                return rep
        return None

    def delete_report(self, report_id: str, user_id: str) -> bool:
        """
        Deletes a specific research report with memory fallback.
        """
        if hasattr(self, "_memory_reports"):
            self._memory_reports.pop(report_id, None)

        try:
            admin = get_supabase_admin()
            admin.table("research_reports").delete().eq("id", report_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            print(f"[ResearchService] Delete report note: {e}")
            return True

    def clear_all_history(self, user_id: str) -> bool:
        """
        Clears all research reports for the authenticated user.
        """
        if hasattr(self, "_memory_reports"):
            keys_to_del = [k for k, v in self._memory_reports.items() if v.get("user_id") == user_id]
            for k in keys_to_del:
                del self._memory_reports[k]

        try:
            admin = get_supabase_admin()
            admin.table("research_reports").delete().eq("user_id", user_id).execute()
            return True
        except Exception as e:
            print(f"[ResearchService] Clear history note: {e}")
            return True

research_service = ResearchService()
