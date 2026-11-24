"""
DocuMind Universal Source Registry & Discovery Engine.
Maintains a comprehensive, modular registry of primary official sources,
government portals, research publishers, company documentation, specialized APIs,
and authoritative databases across 12+ professional domains.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import urllib.parse
import re

class SourceRegistry:
    """
    Extensible Source Registry and Authority Verification Engine.
    Stores metadata for authoritative sources: domain, reliability tier,
    official status, freshness, and verification criteria.
    """

    DOMAINS = {
        "ai_ml": "Artificial Intelligence & Machine Learning",
        "academic_research": "Academic Publications & Research Repositories",
        "software_cybersecurity": "Software Engineering & Cybersecurity",
        "science_tech": "Science, Engineering & Technology",
        "gov_policy": "Government Policies, Schemes & Public Services",
        "law_regulation": "Law, Regulations & Statutory Gazettes",
        "finance_markets": "Finance, Markets & Economic Data",
        "healthcare_medicine": "Healthcare, Medicine & Clinical Trials",
        "education": "Education & Academic Frameworks",
        "business_industry": "Business, Trade & Industry Intelligence",
        "international_affairs": "International Affairs & Multilateral Policy",
        "general_universal": "Universal Authoritative Sources"
    }

    def __init__(self):
        self._sources: Dict[str, Dict[str, Any]] = {}
        self._initialize_core_registry()

    def _initialize_core_registry(self):
        """Populates the initial curated authoritative source database."""
        core_records = [
            # 1. AI & Machine Learning
            {
                "id": "src-ai-openai",
                "name": "OpenAI Documentation & Research",
                "domain": "ai_ml",
                "base_url": "https://platform.openai.com/docs",
                "url_patterns": ["openai.com", "platform.openai.com"],
                "source_type": "company_documentation_release_notes",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "continuous",
                "description": "Official OpenAI developer documentation, API changelogs, model specifications, pricing, and safety cards.",
                "verification_criteria": "Primary vendor API documentation and technical reports."
            },
            {
                "id": "src-ai-anthropic",
                "name": "Anthropic Research & Documentation",
                "domain": "ai_ml",
                "base_url": "https://docs.anthropic.com",
                "url_patterns": ["anthropic.com", "docs.anthropic.com"],
                "source_type": "company_documentation_release_notes",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "continuous",
                "description": "Claude model cards, system prompts, API reference, benchmark release notes, and constitutional AI documentation.",
                "verification_criteria": "Primary vendor developer documentation."
            },
            {
                "id": "src-ai-deepmind",
                "name": "Google DeepMind / Google AI",
                "domain": "ai_ml",
                "base_url": "https://deepmind.google",
                "url_patterns": ["deepmind.google", "ai.google.dev", "blog.google/technology/ai"],
                "source_type": "company_documentation_release_notes",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "continuous",
                "description": "Gemini models, AlphaFold, research breakthroughs, API changelogs, and technical reports.",
                "verification_criteria": "Primary lab technical papers and developer documentation."
            },
            {
                "id": "src-ai-lmsys",
                "name": "LMSYS Chatbot Arena",
                "domain": "ai_ml",
                "base_url": "https://chat.lmsys.org",
                "url_patterns": ["lmsys.org", "chat.lmsys.org"],
                "source_type": "independent_benchmark_authority",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "Crowdsourced open LLM evaluation platform tracking Bradley-Terry Elo ratings and independent battle benchmarks.",
                "verification_criteria": "Independent blind human evaluation and Elo tracking."
            },
            {
                "id": "src-ai-art-analysis",
                "name": "Artificial Analysis",
                "domain": "ai_ml",
                "base_url": "https://artificialanalysis.ai",
                "url_patterns": ["artificialanalysis.ai"],
                "source_type": "independent_benchmark_authority",
                "is_official": False,
                "reliability_tier": "tier_2_verified",
                "freshness": "daily",
                "description": "Independent benchmarking of LLM latency, throughput, quality scores (MMLU-Pro, GPQA), and token pricing.",
                "verification_criteria": "Standardized independent automated benchmarking."
            },
            {
                "id": "src-ai-huggingface",
                "name": "Hugging Face Hub & Papers",
                "domain": "ai_ml",
                "base_url": "https://huggingface.co",
                "url_patterns": ["huggingface.co"],
                "source_type": "open_source_model_repository",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "hourly",
                "description": "Open-weights model weights, Open LLM Leaderboard, dataset cards, and community technical discussions.",
                "verification_criteria": "Open-source model repositories and verified creator accounts."
            },
            {
                "id": "src-ai-swebench",
                "name": "SWE-bench Verified Leaderboard",
                "domain": "ai_ml",
                "base_url": "https://www.swebench.com",
                "url_patterns": ["swebench.com"],
                "source_type": "independent_benchmark_authority",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "weekly",
                "description": "Benchmark testing LLMs on solving real-world GitHub software engineering issues.",
                "verification_criteria": "Standardized unit test execution against real GitHub PRs."
            },

            # 2. Academic Publications & Research
            {
                "id": "src-acad-arxiv",
                "name": "arXiv.org E-Print Archive",
                "domain": "academic_research",
                "base_url": "https://arxiv.org",
                "url_patterns": ["arxiv.org"],
                "source_type": "academic_repository",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "Cornell University open-access repository for physics, mathematics, computer science, and AI papers.",
                "verification_criteria": "Academic preprints with permanent identifier and submission timestamps."
            },
            {
                "id": "src-acad-nature",
                "name": "Nature Portfolio & Springer Nature",
                "domain": "academic_research",
                "base_url": "https://www.nature.com",
                "url_patterns": ["nature.com", "springer.com"],
                "source_type": "peer_reviewed_journal",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "High-impact peer-reviewed scientific journals across multidisciplinary sciences and medicine.",
                "verification_criteria": "Rigorous double-blind peer-review standard."
            },
            {
                "id": "src-acad-openalex",
                "name": "OpenAlex Global Scholarly Dataset",
                "domain": "academic_research",
                "base_url": "https://openalex.org",
                "url_patterns": ["openalex.org"],
                "source_type": "academic_repository",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "Open catalog of hundreds of millions of scholarly publications, authors, citations, and institutions.",
                "verification_criteria": "Cross-referenced bibliographic authority indices."
            },

            # 3. Software Engineering & Cybersecurity
            {
                "id": "src-soft-cisa",
                "name": "CISA (Cybersecurity & Infrastructure Security Agency)",
                "domain": "software_cybersecurity",
                "base_url": "https://www.cisa.gov",
                "url_patterns": ["cisa.gov"],
                "source_type": "primary_official_documentation",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "US government alerts on Known Exploited Vulnerabilities (KEV), advisories, and critical infrastructure directives.",
                "verification_criteria": "Official US DHS cybersecurity authority."
            },
            {
                "id": "src-soft-nvd",
                "name": "NIST National Vulnerability Database (NVD)",
                "domain": "software_cybersecurity",
                "base_url": "https://nvd.nist.gov",
                "url_patterns": ["nvd.nist.gov"],
                "source_type": "primary_official_documentation",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "US government repository of standards-based vulnerability management data (CVEs, CVSS ratings).",
                "verification_criteria": "US National Institute of Standards and Technology."
            },
            {
                "id": "src-soft-github",
                "name": "GitHub Releases & Security Advisories",
                "domain": "software_cybersecurity",
                "base_url": "https://github.com",
                "url_patterns": ["github.com"],
                "source_type": "primary_official_documentation",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "continuous",
                "description": "Direct software version release notes, changelogs, commit diffs, and security disclosures.",
                "verification_criteria": "Signed repository maintainer tags."
            },

            # 4. Government Policies & Public Services
            {
                "id": "src-gov-pib",
                "name": "Press Information Bureau (PIB India)",
                "domain": "gov_policy",
                "base_url": "https://pib.gov.in",
                "url_patterns": ["pib.gov.in"],
                "source_type": "primary_official_documentation",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "hourly",
                "description": "Official nodal agency of the Government of India for disseminating information on government policies, schemes, and cabinet decisions.",
                "verification_criteria": "Official Government of India nodal portal."
            },
            {
                "id": "src-gov-egazette",
                "name": "The Gazette of India (eGazette)",
                "domain": "gov_policy",
                "base_url": "https://egazette.gov.in",
                "url_patterns": ["egazette.gov.in"],
                "source_type": "regulatory_gazette",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "Official public journal and authorized legal document of the Government of India publishing statutory notifications, acts, and orders.",
                "verification_criteria": "Official Government Gazette publication."
            },
            {
                "id": "src-gov-us-fedreg",
                "name": "US Federal Register",
                "domain": "gov_policy",
                "base_url": "https://www.federalregister.gov",
                "url_patterns": ["federalregister.gov"],
                "source_type": "regulatory_gazette",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "Daily journal of the United States Government containing presidential proclamations, executive orders, and federal agency regulations.",
                "verification_criteria": "Official US National Archives and Records Administration."
            },

            # 5. Law & Regulations
            {
                "id": "src-law-indiacode",
                "name": "India Code Digital Repository",
                "domain": "law_regulation",
                "base_url": "https://www.indiacode.nic.in",
                "url_patterns": ["indiacode.nic.in"],
                "source_type": "primary_official_documentation",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "weekly",
                "description": "Official database of all Central and State legislation in India, incorporating enacted amendments and repeal notes.",
                "verification_criteria": "Ministry of Law and Justice, Government of India."
            },
            {
                "id": "src-law-sci",
                "name": "Supreme Court of India Official Judgments",
                "domain": "law_regulation",
                "base_url": "https://www.sci.gov.in",
                "url_patterns": ["sci.gov.in", "main.sci.gov.in"],
                "source_type": "primary_official_documentation",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "Direct orders, judgments, causelists, and constitutional bench verdicts of the Supreme Court of India.",
                "verification_criteria": "Apex judicial portal of India."
            },
            {
                "id": "src-law-eurlex",
                "name": "EUR-Lex (European Union Law)",
                "domain": "law_regulation",
                "base_url": "https://eur-lex.europa.eu",
                "url_patterns": ["eur-lex.europa.eu"],
                "source_type": "primary_official_documentation",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "Official gateway to European Union legal acts, treaties, directives, regulations (e.g., EU AI Act, GDPR).",
                "verification_criteria": "Publications Office of the European Union."
            },

            # 6. Finance, Markets & Economic Developments
            {
                "id": "src-fin-rbi",
                "name": "Reserve Bank of India (RBI)",
                "domain": "finance_markets",
                "base_url": "https://www.rbi.org.in",
                "url_patterns": ["rbi.org.in"],
                "source_type": "financial_regulatory",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "India's central bank and monetary authority: repo rates, MPC resolutions, regulatory circulars, and forex data.",
                "verification_criteria": "Central Banking Statutory Authority."
            },
            {
                "id": "src-fin-sec",
                "name": "U.S. Securities and Exchange Commission (SEC EDGAR)",
                "domain": "finance_markets",
                "base_url": "https://www.sec.gov/edgar",
                "url_patterns": ["sec.gov"],
                "source_type": "financial_regulatory",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "continuous",
                "description": "Public company regulatory disclosures, 10-K annual reports, 10-Q quarterlies, 8-K material updates, and insider transactions.",
                "verification_criteria": "Official US Federal Securities Regulator."
            },
            {
                "id": "src-fin-fed",
                "name": "Federal Reserve System (The Fed)",
                "domain": "finance_markets",
                "base_url": "https://www.federalreserve.gov",
                "url_patterns": ["federalreserve.gov"],
                "source_type": "financial_regulatory",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "US central bank: FOMC rate decisions, monetary policy reports, economic projections, and balance sheet data.",
                "verification_criteria": "US Central Banking Authority."
            },

            # 7. Healthcare & Medicine
            {
                "id": "src-med-who",
                "name": "World Health Organization (WHO)",
                "domain": "healthcare_medicine",
                "base_url": "https://www.who.int",
                "url_patterns": ["who.int"],
                "source_type": "primary_official_documentation",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "Global health guidelines, disease surveillance, clinical recommendations, and international health regulations.",
                "verification_criteria": "United Nations specialized international public health agency."
            },
            {
                "id": "src-med-fda",
                "name": "U.S. Food and Drug Administration (FDA)",
                "domain": "healthcare_medicine",
                "base_url": "https://www.fda.gov",
                "url_patterns": ["fda.gov"],
                "source_type": "primary_official_documentation",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "Drug approvals, medical device clearances (510k), clinical safety warnings, recalls, and pharmaceutical standards.",
                "verification_criteria": "US Department of Health and Human Services."
            },
            {
                "id": "src-med-pubmed",
                "name": "PubMed / National Library of Medicine (NLM)",
                "domain": "healthcare_medicine",
                "base_url": "https://pubmed.ncbi.nlm.nih.gov",
                "url_patterns": ["pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov"],
                "source_type": "academic_repository",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "Premier database of biomedical literature, MEDLINE citations, randomized controlled trials, and clinical studies.",
                "verification_criteria": "US National Institutes of Health (NIH)."
            },

            # 8. International Affairs & Multilateral Policy
            {
                "id": "src-intl-un",
                "name": "United Nations Digital Library",
                "domain": "international_affairs",
                "base_url": "https://digitallibrary.un.org",
                "url_patterns": ["un.org", "digitallibrary.un.org"],
                "source_type": "primary_official_documentation",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "description": "UN General Assembly resolutions, Security Council records, treaty deposits, and international law conventions.",
                "verification_criteria": "Primary multilateral treaty depository."
            },
            {
                "id": "src-intl-wto",
                "name": "World Trade Organization (WTO)",
                "domain": "international_affairs",
                "base_url": "https://www.wto.org",
                "url_patterns": ["wto.org"],
                "source_type": "primary_official_documentation",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "weekly",
                "description": "Global trade rules, tariff agreements, trade policy reviews, and dispute settlement panel reports.",
                "verification_criteria": "Multilateral international trade authority."
            }
        ]

        now_str = datetime.now(timezone.utc).isoformat()
        for rec in core_records:
            rec["last_verified_at"] = now_str
            self._sources[rec["id"]] = rec

    def register_source(self, source_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extensible method to register a new authoritative source provider dynamically.
        """
        src_id = source_dict.get("id") or f"src-dyn-{len(self._sources) + 1}"
        domain = source_dict.get("domain", "general_universal")
        
        record = {
            "id": src_id,
            "name": source_dict.get("name", "Custom Authoritative Source"),
            "domain": domain,
            "domain_label": self.DOMAINS.get(domain, domain.replace("_", " ").title()),
            "base_url": source_dict.get("base_url", ""),
            "url_patterns": source_dict.get("url_patterns", []),
            "source_type": source_dict.get("source_type", "secondary_verified_source"),
            "is_official": bool(source_dict.get("is_official", False)),
            "reliability_tier": source_dict.get("reliability_tier", "tier_2_verified"),
            "freshness": source_dict.get("freshness", "daily"),
            "description": source_dict.get("description", "Registered research authority"),
            "verification_criteria": source_dict.get("verification_criteria", "Cross-verified editorial standards"),
            "last_verified_at": datetime.now(timezone.utc).isoformat()
        }
        self._sources[src_id] = record
        return record

    def list_domains(self) -> List[Dict[str, str]]:
        """Returns list of all supported professional research domains."""
        return [{"id": k, "label": v} for k, v in self.DOMAINS.items()]

    def list_sources(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists sources registered in the catalog, optionally filtered by domain."""
        res = []
        for s in self._sources.values():
            if domain and domain != "all" and s["domain"] != domain:
                continue
            item = dict(s)
            item["domain_label"] = self.DOMAINS.get(s["domain"], s["domain"].title())
            res.append(item)
        return res

    def match_source_metadata(self, url: str) -> Dict[str, Any]:
        """
        Inspects any target URL and matches it against registered sources to
        retrieve reliability tier, official classification, freshness, and authority score.
        """
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()

        # Check explicit registry matches
        for s in self._sources.values():
            for pat in s.get("url_patterns", []):
                if pat in netloc:
                    return {
                        "registered": True,
                        "source_name": s["name"],
                        "domain": s["domain"],
                        "domain_label": self.DOMAINS.get(s["domain"], s["domain"].title()),
                        "source_type": s["source_type"],
                        "is_official": s["is_official"],
                        "reliability_tier": s["reliability_tier"],
                        "freshness": s["freshness"],
                        "verification_criteria": s["verification_criteria"],
                        "last_verified_at": s["last_verified_at"]
                    }

        # Fallback heuristic classification
        is_gov = any(g in netloc for g in [".gov", ".nic.in", ".gov.in", ".gov.uk", ".europa.eu"])
        is_edu = any(e in netloc for e in [".edu", ".ac.uk", ".ac.in"])
        is_org = ".org" in netloc

        if is_gov:
            return {
                "registered": False,
                "source_name": netloc,
                "domain": "gov_policy",
                "domain_label": "Government & Public Services",
                "source_type": "primary_official_documentation",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "daily",
                "verification_criteria": "Official Government TLD (.gov / .nic.in)",
                "last_verified_at": datetime.now(timezone.utc).isoformat()
            }
        elif is_edu:
            return {
                "registered": False,
                "source_name": netloc,
                "domain": "academic_research",
                "domain_label": "Academic & Research Institution",
                "source_type": "academic_repository",
                "is_official": True,
                "reliability_tier": "tier_1_authoritative",
                "freshness": "weekly",
                "verification_criteria": "Accredited Academic Institution Domain (.edu / .ac)",
                "last_verified_at": datetime.now(timezone.utc).isoformat()
            }
        elif is_org:
            return {
                "registered": False,
                "source_name": netloc,
                "domain": "general_universal",
                "domain_label": "Institutional Organization",
                "source_type": "secondary_verified_source",
                "is_official": False,
                "reliability_tier": "tier_2_verified",
                "freshness": "weekly",
                "verification_criteria": "Non-Profit Organization / Working Group",
                "last_verified_at": datetime.now(timezone.utc).isoformat()
            }

        return {
            "registered": False,
            "source_name": netloc,
            "domain": "general_universal",
            "domain_label": "Secondary Web Source",
            "source_type": "secondary_web_reporting",
            "is_official": False,
            "reliability_tier": "tier_3_general",
            "freshness": "unknown",
            "verification_criteria": "General Web Publication",
            "last_verified_at": datetime.now(timezone.utc).isoformat()
        }

    def evaluate_source_quality(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Assesses overall source balance, diversity, and reliability.
        Flags single-search-engine bias or lack of official primary verification.
        """
        total = len(sources)
        if total == 0:
            return {
                "quality_score": 0,
                "tier_1_count": 0,
                "tier_2_count": 0,
                "tier_3_count": 0,
                "official_primary_ratio": 0.0,
                "single_provider_bias_warning": False,
                "notes": ["No sources retrieved to evaluate."]
            }

        tier_1 = 0
        tier_2 = 0
        tier_3 = 0
        official = 0
        domains_seen = set()

        for s in sources:
            url = s.get("url", "")
            meta = self.match_source_metadata(url)
            rel_tier = meta.get("reliability_tier", "tier_3_general")
            if "tier_1" in rel_tier:
                tier_1 += 1
            elif "tier_2" in rel_tier:
                tier_2 += 1
            else:
                tier_3 += 1

            if meta.get("is_official") or s.get("is_official"):
                official += 1

            domains_seen.add(meta.get("domain", "general_universal"))

        official_ratio = round(official / total, 2)
        # Quality score out of 100
        quality_score = min(100, int((tier_1 * 25) + (tier_2 * 15) + (tier_3 * 5) + (len(domains_seen) * 5)))

        notes = []
        if official_ratio >= 0.5:
            notes.append("High confidence: Grounded predominantly in primary official or peer-reviewed authorities.")
        elif official_ratio > 0:
            notes.append("Moderate confidence: Blends official sources with secondary industry analysis.")
        else:
            notes.append("Advisory: Relies primarily on secondary web commentary. Cross-verify with primary gazettes or official docs.")

        if len(domains_seen) == 1:
            notes.append("Domain concentration: Sources are concentrated in a single domain.")

        return {
            "quality_score": quality_score,
            "total_sources": total,
            "tier_1_count": tier_1,
            "tier_2_count": tier_2,
            "tier_3_count": tier_3,
            "official_primary_count": official,
            "official_primary_ratio": official_ratio,
            "domains_covered": list(domains_seen),
            "single_provider_bias_warning": len(domains_seen) == 1 and total > 2,
            "notes": notes
        }

source_registry = SourceRegistry()
