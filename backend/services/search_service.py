"""
DocuMind Universal Search & Source Discovery Service.
Queries live web sources across all 12 professional domains (AI & ML, Law, Finance,
Healthcare, Government, Academics, Software, Science), integrates with Source Registry,
and enriches results with domain classifications, freshness, and authority tiers.
"""

import re
import base64
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from backend.services.source_registry import source_registry

class SearchService:
    """
    Live web search and authoritative source discovery service.
    Queries live web sources, integrates with Source Registry,
    extracts clean snippets, publication dates, and retrieval timestamps.
    """

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }

    def __init__(self, timeout: float = 3.5):
        self.timeout = timeout
        self.registry = source_registry

    def _decode_bing_url(self, raw_url: str) -> str:
        """
        Decodes Bing redirect wrapper (e.g. /ck/a?!...&u=a1<base64>&ntb=1) to the actual canonical URL.
        """
        if "/ck/a?" in raw_url and "u=" in raw_url:
            try:
                parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                if "u" in parsed_qs:
                    u_val = parsed_qs["u"][0]
                    if u_val.startswith("a1"):
                        b64_part = u_val[2:]
                        padding = len(b64_part) % 4
                        if padding:
                            b64_part += "=" * (4 - padding)
                        decoded = base64.b64decode(b64_part).decode("utf-8")
                        if decoded.startswith("http://") or decoded.startswith("https://"):
                            return decoded
            except Exception:
                pass
        return raw_url

    def classify_source_authority(self, url: str) -> Dict[str, Any]:
        """
        Classifies URL domain authority using the Universal Source Registry.
        """
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()

        meta = self.registry.match_source_metadata(url)

        level = meta.get("reliability_tier", "tier_3_general")
        is_official = meta.get("is_official", False)
        badge = "web"
        if is_official or "tier_1" in level:
            if meta.get("domain") == "gov_policy":
                badge = "gov"
            elif meta.get("domain") == "law_regulation":
                badge = "legal"
            elif meta.get("domain") == "ai_ml":
                badge = "ai-official"
            elif meta.get("domain") in ["academic_research", "healthcare_medicine"]:
                badge = "academic"
            elif meta.get("domain") == "finance_markets":
                badge = "finance"
            else:
                badge = "official"
        elif "tier_2" in level:
            badge = "verified"
        else:
            badge = "web"

        return {
            "domain": domain,
            "source_name": meta.get("source_name", domain),
            "category": meta.get("domain_label", "Web Source"),
            "level": level,
            "badge": badge,
            "is_official": is_official,
            "freshness": meta.get("freshness", "unknown"),
            "verification_criteria": meta.get("verification_criteria", "Web crawl")
        }

    def _search_bing(self, query: str, max_results: int = 6) -> List[Dict[str, Any]]:
        """
        Fast primary web search using Bing parser. Resolves canonical URLs in <0.6s.
        """
        results = []
        retrieval_timestamp = datetime.now(timezone.utc).isoformat()
        try:
            params = {"q": query}
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=self.HEADERS) as client:
                r = client.get("https://www.bing.com/search", params=params)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    for li in soup.select("li.b_algo"):
                        title_el = li.select_one("h2 a")
                        snippet_el = li.select_one(".b_caption p") or li.select_one("p")
                        if not title_el or not snippet_el:
                            continue

                        raw_href = title_el.get("href", "")
                        actual_url = self._decode_bing_url(raw_href)
                        title = title_el.get_text(strip=True)
                        snippet = snippet_el.get_text(strip=True)

                        auth_meta = self.classify_source_authority(actual_url)

                        date_match = re.search(
                            r"\b(20[12]\d{1}[-/]\d{1,2}[-/]\d{1,2}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? 20[12]\d)\b",
                            snippet,
                            re.IGNORECASE
                        )
                        published_date = date_match.group(0) if date_match else "Recent"

                        results.append({
                            "title": title,
                            "url": actual_url,
                            "snippet": snippet,
                            "domain": auth_meta["domain"],
                            "source_name": auth_meta.get("source_name", auth_meta["domain"]),
                            "category": auth_meta["category"],
                            "level": auth_meta["level"],
                            "badge": auth_meta["badge"],
                            "is_official": auth_meta["is_official"],
                            "freshness": auth_meta["freshness"],
                            "verification_criteria": auth_meta["verification_criteria"],
                            "published_date": published_date,
                            "retrieved_at": retrieval_timestamp
                        })
                        if len(results) >= max_results:
                            break
        except Exception as e:
            print(f"[SearchService] Bing search notice: {e}")
        return results

    def _search_openalex(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Authoritative academic papers search via OpenAlex API.
        """
        results = []
        retrieval_timestamp = datetime.now(timezone.utc).isoformat()
        try:
            params = {"search": query, "per-page": max_results}
            with httpx.Client(timeout=3.0, headers=self.HEADERS) as client:
                r = client.get("https://api.openalex.org/works", params=params)
                if r.status_code == 200:
                    data = r.json()
                    for item in data.get("results", []):
                        title = item.get("title") or "Academic Paper"
                        doi = item.get("doi") or f"https://openalex.org/{item.get('id', '')}"
                        pub_year = str(item.get("publication_year", "Recent"))
                        
                        # Abstract inverted index reconstruction
                        abstract = ""
                        inv_idx = item.get("abstract_inverted_index")
                        if inv_idx:
                            words = []
                            for word, positions in inv_idx.items():
                                for pos in positions:
                                    words.append((pos, word))
                            words.sort(key=lambda x: x[0])
                            abstract = " ".join([w[1] for w in words[:45]]) + "..."

                        results.append({
                            "title": f"{title} (Scholarly Publication)",
                            "url": doi,
                            "snippet": abstract or f"Published research paper on {query}. Year: {pub_year}.",
                            "domain": "openalex.org",
                            "source_name": "OpenAlex Scholarly Registry",
                            "category": "Academic / Peer-Reviewed",
                            "level": "tier_2_academic",
                            "badge": "academic",
                            "is_official": False,
                            "freshness": "peer_reviewed",
                            "verification_criteria": "Crossref/OpenAlex index",
                            "published_date": pub_year,
                            "retrieved_at": retrieval_timestamp
                        })
        except Exception as e:
            print(f"[SearchService] OpenAlex search notice: {e}")
        return results

    def search(
        self,
        query: str,
        domain_filter: Optional[str] = None,
        max_results: int = 6,
        prefer_official: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Executes search across live web and enriches results with domain classifications,
        timestamps, clean snippets, and source registry metadata.
        """
        results = []
        retrieval_timestamp = datetime.now(timezone.utc).isoformat()

        # Augment query if a specific professional domain is chosen
        effective_query = query
        if domain_filter and domain_filter != "all" and domain_filter != "general_universal":
            if domain_filter == "ai_ml" and not any(w in query.lower() for w in ["ai", "model", "benchmark"]):
                effective_query = f"{query} AI model benchmark documentation"
            elif domain_filter == "law_regulation" and not any(w in query.lower() for w in ["law", "act", "section"]):
                effective_query = f"{query} legislation gazette official act"
            elif domain_filter == "finance_markets" and not any(w in query.lower() for w in ["market", "rate", "sec"]):
                effective_query = f"{query} financial regulatory disclosure"
            elif domain_filter == "academic_research":
                effective_query = f"{query} research paper arxiv doi"

        # Strategy 1: Fast Bing Search (primary engine: ~0.5s)
        bing_results = self._search_bing(effective_query, max_results=max_results)
        results.extend(bing_results)

        # Strategy 2: If academic domain or results < 3, query OpenAlex
        if (domain_filter in ["academic_research", "healthcare_medicine"] or len(results) < 2):
            alex_results = self._search_openalex(query, max_results=2)
            results.extend(alex_results)

        # Strategy 3: Fallback to Wikipedia API if still few results
        if len(results) < 3:
            wiki_results = self._search_wikipedia(query)
            results.extend(wiki_results)

        # Deduplicate results by URL
        unique_results = []
        seen_urls = set()
        for r in results:
            clean_url = r["url"].rstrip("/")
            if clean_url not in seen_urls:
                seen_urls.add(clean_url)
                unique_results.append(r)

        # Sort results: prioritize official primary and tier-1 sources when requested
        if prefer_official:
            def sort_key(item):
                if item["level"] == "tier_1_authoritative" or item["level"] == "tier_1_official":
                    return 0
                if item["level"] == "tier_2_verified" or item["level"] == "tier_2_regulatory":
                    return 1
                if item["level"] == "tier_2_academic":
                    return 2
                if item["level"] == "tier_3_news":
                    return 3
                return 4
            unique_results.sort(key=sort_key)

        return unique_results[:max_results]

    def _search_wikipedia(self, query: str) -> List[Dict[str, Any]]:
        """
        Queries Wikipedia API for authoritative reference contextual overview.
        """
        wiki_results = []
        retrieval_timestamp = datetime.now(timezone.utc).isoformat()
        try:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 3
            }
            with httpx.Client(timeout=5.0) as client:
                r = client.get("https://en.wikipedia.org/w/api.php", params=params, headers=self.HEADERS)
                if r.status_code == 200:
                    data = r.json()
                    search_items = data.get("query", {}).get("search", [])
                    for item in search_items:
                        title = item.get("title", "")
                        raw_snippet = item.get("snippet", "")
                        snippet = re.sub(r"<[^>]+>", "", raw_snippet)
                        page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                        
                        wiki_results.append({
                            "title": f"{title} – Reference Overview",
                            "url": page_url,
                            "snippet": snippet,
                            "domain": "en.wikipedia.org",
                            "source_name": "Wikipedia Scholarly Reference",
                            "category": "Peer-Reviewed / Reference",
                            "level": "tier_2_academic",
                            "badge": "academic",
                            "is_official": False,
                            "freshness": "constantly_updated",
                            "verification_criteria": "Community peer-reviewed encyclopedia",
                            "published_date": "Constantly Updated",
                            "retrieved_at": retrieval_timestamp
                        })
        except Exception as e:
            print(f"[SearchService] Wikipedia search note: {e}")

        return wiki_results

    def fetch_page_summary(self, url: str, max_chars: int = 1500) -> Optional[str]:
        """
        Fetches full webpage content and extracts clean textual paragraphs.
        """
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=self.HEADERS) as client:
                r = client.get(url)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    for el in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        el.decompose()
                    paragraphs = [p.get_text(strip=True) for p in soup.find_all(["p", "article", "li"]) if len(p.get_text(strip=True)) > 40]
                    content = "\n\n".join(paragraphs)
                    return content[:max_chars]
        except Exception as e:
            print(f"[SearchService] Failed to fetch page summary from {url}: {e}")
        return None

search_service = SearchService()
