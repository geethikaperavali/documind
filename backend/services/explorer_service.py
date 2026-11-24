import time
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.database import get_supabase_admin
from backend.services.gemini_gateway import gemini_gateway

class ExplorerService:
    """
    DocuMind Knowledge Explorer & Graph Extraction Engine.
    Extracts entities, concepts, statutory references, organizations, and their
    inter-relationships from user documents to construct an interactive Knowledge Graph.
    Features TTL-based graph result caching for instantaneous page transitions.
    """

    GRAPH_SYSTEM_PROMPT = """You are DocuMind's Senior Knowledge Graph & Entity Extraction Architect.
Your task is to analyze document chunks and extract a connected Knowledge Graph of entities and semantic relationships.

ENTITY TYPES:
- "statute": Laws, sections, acts, regulations, standards, articles
- "organization": Government bodies, courts, companies, regulatory agencies
- "person": Key authors, judges, officials, signatories
- "concept": Core principles, technical frameworks, doctrines, definitions
- "temporal_date": Key effective dates, deadlines, milestone years, sunset dates

RELATION TYPES:
- "amends" / "repeals" / "supersedes"
- "governs" / "regulates" / "enacted_by"
- "defines" / "implements" / "depends_on"
- "complies_with" / "violates"

Return valid JSON conforming to this schema:
{
  "entities": [
    {
      "id": "normalized_snake_case_id",
      "label": "Display Name",
      "type": "statute | organization | person | concept | temporal_date",
      "description": "1-sentence definition of role in text"
    }
  ],
  "relations": [
    {
      "source": "source_entity_id",
      "target": "target_entity_id",
      "relation": "amends | governs | defines | implements | depends_on | supersedes",
      "evidence": "Brief supporting clause excerpt"
    }
  ]
}
"""

    def __init__(self):
        self._graph_cache: Dict[str, Any] = {}

    def extract_document_knowledge_graph(
        self,
        document_id: Optional[str],
        user_id: str,
        refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Extracts entities and relationships for a specific document or across all user documents.
        Utilizes caching unless refresh=True is requested.
        """
        cache_key = f"{user_id}:{document_id or 'all'}"
        now_ts = time.time()

        if not refresh and cache_key in self._graph_cache:
            entry = self._graph_cache[cache_key]
            # 30-minute cache TTL
            if now_ts - entry["timestamp"] < 1800:
                cached_data = dict(entry["data"])
                cached_data["cached"] = True
                return cached_data

        admin = get_supabase_admin()

        # 1. Fetch chunks
        query = admin.table("document_chunks").select("id, document_id, content, page_number")
        if document_id and document_id != "all":
            query = query.eq("document_id", document_id).eq("user_id", user_id)
        else:
            query = query.eq("user_id", user_id)
        
        chunks = query.limit(20).execute().data or []
        if not chunks:
            empty_graph = {
                "nodes": [],
                "links": [],
                "total_entities": 0,
                "total_relationships": 0,
                "summary": "No document content found in your knowledge base. Upload documents in Knowledge Base to generate your Knowledge Graph.",
                "cached": False
            }
            self._graph_cache[cache_key] = {"timestamp": now_ts, "data": empty_graph}
            return empty_graph

        # 2. Fetch document names map
        docs = admin.table("documents").select("id, name").eq("user_id", user_id).execute().data or []
        doc_names = {d["id"]: d["name"] for d in docs}

        sample_text = "\n\n".join([f"[{doc_names.get(c.get('document_id'), 'Doc')} | Page {c.get('page_number', 1)}]: {c.get('content', '')}" for c in chunks[:12]])

        user_prompt = f"""EXTRACT CONNECTED KNOWLEDGE GRAPH FROM THESE DOCUMENT EXCERPTS:

{sample_text[:8000]}

Extract top key entities and their semantic interconnections. Return JSON matching GRAPH_SYSTEM_PROMPT.
"""
        default_fallback = {
            "entities": [
                {"id": "documind_core", "label": "Document Intelligence", "type": "concept", "description": "Central knowledge domain"}
            ],
            "relations": []
        }

        graph_raw = gemini_gateway.generate_json(
            prompt=user_prompt,
            system_instruction=self.GRAPH_SYSTEM_PROMPT,
            temperature=0.1,
            default_fallback=default_fallback
        )

        # 3. Format nodes and links for visual canvas
        nodes = []
        entity_ids = set()

        for ent in graph_raw.get("entities", []):
            eid = ent.get("id", "").strip().lower().replace(" ", "_")
            if not eid or eid in entity_ids:
                continue
            entity_ids.add(eid)

            nodes.append({
                "id": eid,
                "label": ent.get("label", eid),
                "name": ent.get("label", eid),
                "category": ent.get("type", "concept"),
                "type": ent.get("type", "concept"),
                "description": ent.get("description", ""),
                "group": ent.get("type", "concept")
            })

        links = []
        for rel in graph_raw.get("relations", []):
            src = rel.get("source", "").strip().lower().replace(" ", "_")
            tgt = rel.get("target", "").strip().lower().replace(" ", "_")
            if src in entity_ids and tgt in entity_ids and src != tgt:
                links.append({
                    "source": src,
                    "target": tgt,
                    "relation": rel.get("relation", "connected_to"),
                    "evidence": rel.get("evidence", "")
                })

        result = {
            "nodes": nodes,
            "links": links,
            "total_entities": len(nodes),
            "total_relationships": len(links),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cached": False
        }

        # Cache extracted graph
        self._graph_cache[cache_key] = {"timestamp": now_ts, "data": result}
        return result

explorer_service = ExplorerService()
