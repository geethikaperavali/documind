import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.services.gemini_gateway import gemini_gateway
from backend.services.rag_service import rag_service
from backend.services.search_service import search_service
from backend.services.temporal_intelligence import temporal_service
from backend.services.ai_intelligence import ai_intelligence_service

class IntelligentOrchestrator:
    """
    DocuMind Intelligent Orchestration Layer.
    Determines optimal execution strategy across:
    1. Private RAG retrieval (internal document context)
    2. Live authoritative web search (external reality)
    3. AI Industry Intelligence (benchmarks, pricing, model comparisons, deprecations)
    4. Temporal Intelligence (historical vs. current status, repeals, amendments)
    5. Hybrid fusion (comparing document claims against current external world)
    """

    def classify_intent(self, question: str, has_user_docs: bool = True) -> str:
        """
        Fast heuristic and AI intent classifier.
        """
        lower = question.lower()

        # Rule 1: Hybrid cues (evaluating a user document against external laws/regulations)
        has_doc_reference = any(w in lower for w in ["my document", "my doc", "my contract", "our policy", "this file", "in my document", "uploaded"])
        if has_doc_reference and any(kw in lower for kw in ["comply", "compliance", "compare", "outdated", "amended", "repealed", "valid", "act", "law", "regulation"]):
            return "HYBRID"

        # Rule 2: High-confidence Temporal triggers
        temporal_keywords = [
            "still valid", "still in force", "repealed", "amended", "superseded",
            "what changed", "historical position", "current position", "bns",
            "bharatiya nyaya", "effective date", "section 377", "outdated", "sunset"
        ]
        if any(kw in lower for kw in temporal_keywords) or temporal_service.is_time_sensitive(question):
            return "TEMPORAL_VERIFY"

        # Rule 3: AI Industry Intelligence triggers
        if ai_intelligence_service.is_ai_industry_query(question):
            if not has_doc_reference:
                return "AI_INTELLIGENCE"

        # Rule 4: Web research explicit cues
        web_keywords = ["search web", "live web", "latest news", "market share", "industry trends", "government scheme 2025"]
        if any(kw in lower for kw in web_keywords):
            return "WEB_RESEARCH"

        # Default to private RAG if user has documents, else web research
        return "PRIVATE_RAG" if has_user_docs else "WEB_RESEARCH"

    def orchestrate_query(
        self,
        question: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        force_mode: Optional[str] = None,
        has_user_docs: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates query execution through private RAG, web search, AI intelligence, or temporal intelligence.
        Uses concurrent execution for multi-source pathways.
        """
        # Determine whether user has uploaded documents if not explicitly passed
        if has_user_docs is None:
            try:
                from backend.database import get_supabase_admin
                admin = get_supabase_admin()
                doc_check = admin.table("documents").select("id", count="exact").eq("user_id", user_id).eq("status", "ready").limit(1).execute()
                has_user_docs = bool(doc_check.count and doc_check.count > 0) or bool(doc_check.data and len(doc_check.data) > 0)
            except Exception:
                has_user_docs = False

        mode = force_mode or self.classify_intent(question, has_user_docs=has_user_docs)
        timestamp = datetime.now(timezone.utc).isoformat()
        lower = question.lower()

        # =========================================================================
        # 1. TEMPORAL INTELLIGENCE STRATEGY
        # =========================================================================
        if mode == "TEMPORAL_VERIFY":
            # Only query user document chunks if user explicitly refers to their files
            doc_chunks = []
            historical_context = None
            has_doc_cue = any(w in lower for w in ["my document", "my doc", "my contract", "our policy", "this file", "in my"])

            if has_doc_cue:
                try:
                    doc_chunks = rag_service.retrieve_relevant_chunks(question, user_id=user_id, top_k=2)
                    if doc_chunks:
                        historical_context = "From user's uploaded documents:\n" + "\n".join([f"- {c.get('content', '')[:250]}" for c in doc_chunks])
                except Exception as e:
                    print(f"[Orchestrator] Document chunk lookup skipped: {e}")

            temporal_verdict = temporal_service.verify_temporal_status(question, historical_context=historical_context)

            formatted_answer = f"""### ⏱️ Temporal Intelligence Analysis: {temporal_verdict.get('subject')}
**Status Classification:** `{temporal_verdict.get('status_classification')}` | **Risk Assessment:** `{temporal_verdict.get('risk_assessment')}`

1. **Historical Position:**  
{temporal_verdict.get('historical_position')}

2. **Current Verified Position:**  
{temporal_verdict.get('current_position')}

3. **What Changed:**  
{temporal_verdict.get('what_changed')}

4. **Effective / Commencement Date:**  
{temporal_verdict.get('effective_date')}

5. **Current Applicable Provision / Standard:**  
{temporal_verdict.get('current_applicable_provision')}

6. **Executive Summary:**  
{temporal_verdict.get('executive_summary')}

---
*Verified against authoritative legal and regulatory sources at `{timestamp}`.*
"""
            sources = []
            for s in temporal_verdict.get("official_sources", []):
                sources.append({
                    "document_name": f"[External Web] {s.get('title', 'Authoritative Source')}",
                    "page_number": s.get("badge", "official").upper(),
                    "similarity": 0.95,
                    "snippet": s.get("url", ""),
                    "url": s.get("url")
                })
            for c in doc_chunks:
                sources.append({
                    "document_name": c.get("document_name", "Document"),
                    "page_number": c.get("page_number", 1),
                    "similarity": c.get("similarity", 0.8),
                    "snippet": c.get("content", "")[:200]
                })

            return {
                "answer": formatted_answer,
                "sources": sources,
                "orchestration_mode": "TEMPORAL_VERIFY",
                "temporal_verdict": temporal_verdict
            }

        # =========================================================================
        # 2. AI INDUSTRY INTELLIGENCE STRATEGY
        # =========================================================================
        elif mode == "AI_INTELLIGENCE":
            matrix = ai_intelligence_service.generate_model_comparison_matrix(query=question)
            models = matrix.get("models", [])
            summary = matrix.get("comparison_summary", "")
            disclaimer = matrix.get("methodology_disclaimer", "")

            # Build markdown table of models and benchmarks
            table_md = "\n| Model | Developer | Context | Input / 1M | Output / 1M | Weights | Status |\n"
            table_md += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
            for m in models:
                p_in = m.get("pricing", {}).get("input_per_1m", "N/A") if isinstance(m.get("pricing"), dict) else "N/A"
                p_out = m.get("pricing", {}).get("output_per_1m", "N/A") if isinstance(m.get("pricing"), dict) else "N/A"
                table_md += f"| **{m.get('name')}** | {m.get('developer')} | {m.get('context_window')} | {p_in} | {p_out} | {m.get('weights')} | `{m.get('status')}` |\n"

            evals_md = ""
            for m in models:
                v_claims = m.get("vendor_claims", [])
                i_evals = m.get("independent_evaluations", [])
                evals_md += f"\n#### 🔬 {m.get('name')} Evaluation Profile\n"
                evals_md += f"- **Key Strengths:** {m.get('key_strengths', 'General reasoning and synthesis')}\n"
                if m.get("deprecation_status") and m.get("deprecation_status") != "None":
                    evals_md += f"- **⚠️ Deprecation Notice:** {m.get('deprecation_status')}\n"
                
                if v_claims:
                    evals_md += "- **Vendor-Reported Claims:** " + ", ".join([f"{v.get('benchmark')}: {v.get('score')} ({v.get('notes', 'Vendor Report')})" for v in v_claims]) + "\n"
                if i_evals:
                    evals_md += "- **Independent Evaluations:** " + ", ".join([f"{ie.get('benchmark')}: {ie.get('score')} (Evaluator: {ie.get('evaluator')})" for ie in i_evals]) + "\n"

            formatted_answer = f"""### 🤖 AI Industry Intelligence: Model & Benchmark Analysis

{summary}

{table_md}
{evals_md}

> **Methodology Note:** {disclaimer}
"""
            sources = [
                {
                    "document_name": "[AI Registry] LMSYS Chatbot Arena",
                    "page_number": "BENCHMARK",
                    "similarity": 0.98,
                    "snippet": "Independent crowdsourced human preference Elo leaderboard.",
                    "url": "https://chat.lmsys.org"
                },
                {
                    "document_name": "[AI Registry] SWE-bench Verified",
                    "page_number": "EVALUATION",
                    "similarity": 0.95,
                    "snippet": "Software engineering issue resolution benchmark.",
                    "url": "https://www.swebench.com"
                },
                {
                    "document_name": "[AI Registry] Official Model Specifications & Pricing",
                    "page_number": "SPECS",
                    "similarity": 0.92,
                    "snippet": "Direct vendor release notes and pricing matrices.",
                    "url": "https://platform.openai.com/docs"
                }
            ]

            return {
                "answer": formatted_answer,
                "sources": sources,
                "orchestration_mode": "AI_INTELLIGENCE",
                "ai_matrix": matrix
            }

        # =========================================================================
        # 3. HYBRID STRATEGY (Concurrent Document Retrieval + Web Search)
        # =========================================================================
        elif mode == "HYBRID":
            # Concurrently execute RAG chunk retrieval and web search
            chunks = []
            web_sources = []

            def fetch_doc_chunks():
                try:
                    return rag_service.retrieve_relevant_chunks(question, user_id=user_id, top_k=4)
                except Exception as e:
                    print(f"[Orchestrator] Hybrid doc chunks error: {e}")
                    return []

            def fetch_web_sources():
                try:
                    return search_service.search(f"{question} official law guidance 2024 2025", max_results=4, prefer_official=True)
                except Exception as e:
                    print(f"[Orchestrator] Hybrid web search error: {e}")
                    return []

            with ThreadPoolExecutor(max_workers=2) as executor:
                f_docs = executor.submit(fetch_doc_chunks)
                f_web = executor.submit(fetch_web_sources)
                chunks = f_docs.result()
                web_sources = f_web.result()

            doc_context = "\n\n".join([f"[Document: {c.get('document_name')} | Page {c.get('page_number')}]:\n{c.get('content')}" for c in chunks])
            web_context = "\n\n".join([f"[Live Source: {s['title']} ({s['category']}) | URL: {s['url']}]:\n{s['snippet']}" for s in web_sources])

            prompt = f"""You are DocuMind's Hybrid Intelligence Engine.
Answer the user's question by synthesizing BOTH their private uploaded document context AND verified live external sources.

USER QUESTION:
"{question}"

=== [INTERNAL] USER UPLOADED DOCUMENT CONTEXT ===
{doc_context if doc_context else "No matching internal document content."}

=== [EXTERNAL] LIVE VERIFIED SOURCES RETRIEVED AT {timestamp} ===
{web_context if web_context else "No external web sources retrieved."}

STRICT GROUNDING & PROVENANCE RULES:
1. Clearly distinguish between what the user's document states versus what current external law/reality mandates.
2. If there are contradictions or outdated clauses in the document, explicitly call them out.
3. Cite internal sources as [DocumentName, Page X] and external sources as [SourceTitle, Domain].
"""
            try:
                answer = gemini_gateway.generate_text(prompt=prompt, temperature=0.2)
            except Exception as e:
                print(f"[Orchestrator] Hybrid synthesis error: {e}")
                answer = "Hybrid synthesis could not complete due to temporary AI unavailability."

            sources = []
            for c in chunks:
                sources.append({
                    "document_name": c.get("document_name", "Document"),
                    "page_number": c.get("page_number", 1),
                    "similarity": c.get("similarity", 0.85),
                    "snippet": c.get("content", "")[:200]
                })
            for s in web_sources:
                sources.append({
                    "document_name": f"[Live Web] {s['title']}",
                    "page_number": s.get("badge", "web").upper(),
                    "similarity": 0.90,
                    "snippet": s["snippet"][:200],
                    "url": s["url"]
                })

            return {
                "answer": answer,
                "sources": sources,
                "orchestration_mode": "HYBRID"
            }

        # =========================================================================
        # 4. WEB RESEARCH STRATEGY
        # =========================================================================
        elif mode == "WEB_RESEARCH":
            web_sources = search_service.search(question, max_results=5, prefer_official=True)
            sources_summary = "\n\n".join([f"[Source {i}: {s['domain']} | {s['published_date']}]:\nTitle: {s['title']}\nSnippet: {s['snippet']}\nURL: {s['url']}" for i, s in enumerate(web_sources, 1)])

            prompt = f"""You are DocuMind's Real-Time Web Research Assistant.
Answer the user's question based strictly on these live retrieved authoritative sources.

QUESTION: "{question}"

RETRIEVED LIVE SOURCES ({timestamp}):
{sources_summary}

Provide a well-structured, comprehensive answer citing [Source X: Domain, Date].
"""
            try:
                answer = gemini_gateway.generate_text(prompt=prompt, temperature=0.2)
            except Exception as e:
                print(f"[Orchestrator] Web research generation error: {e}")
                answer = "Research answer generation failed due to transient API latency."

            sources = [{
                "document_name": f"[Live Web] {s['title']}",
                "page_number": s.get("badge", "web").upper(),
                "similarity": 0.90,
                "snippet": s["snippet"][:200],
                "url": s["url"]
            } for s in web_sources]

            return {
                "answer": answer,
                "sources": sources,
                "orchestration_mode": "WEB_RESEARCH"
            }

        # =========================================================================
        # 5. PRIVATE RAG STRATEGY (Default)
        # =========================================================================
        else:
            rag_res = rag_service.answer_question(
                question=question,
                user_id=user_id,
                conversation_history=conversation_history
            )

            # If user has zero document chunks retrieved AND the query does not explicitly ask about their document,
            # gracefully fall back to web research so zero-document users never encounter an empty dead-end!
            has_doc_cue = any(w in lower for w in ["my document", "my doc", "my contract", "our policy", "this file", "in my document", "uploaded", "chunk"])
            if not rag_res.get("sources") and not has_doc_cue:
                try:
                    web_sources = search_service.search(question, max_results=4, prefer_official=True)
                    if web_sources:
                        sources_summary = "\n\n".join([f"[{s['title']}]: {s['snippet']} (URL: {s['url']})" for s in web_sources])
                        gen_prompt = f"""You are DocuMind AI, an intelligent document & research assistant.
Answer the user's question clearly, thoroughly, and authoritatively based on current information.

USER QUESTION: "{question}"

RETRIEVED REFERENCES ({timestamp}):
{sources_summary}
"""
                        answer = gemini_gateway.generate_text(prompt=gen_prompt, temperature=0.2)
                        return {
                            "answer": answer,
                            "sources": [{
                                "document_name": f"[Live Web] {s['title']}",
                                "page_number": s.get("badge", "web").upper(),
                                "similarity": 0.90,
                                "snippet": s["snippet"][:200],
                                "url": s["url"]
                            } for s in web_sources],
                            "orchestration_mode": "WEB_RESEARCH"
                        }
                except Exception as fallback_err:
                    print(f"[Orchestrator] Zero-doc fallback notice: {fallback_err}")

            rag_res["orchestration_mode"] = "PRIVATE_RAG"
            return rag_res

orchestrator = IntelligentOrchestrator()
