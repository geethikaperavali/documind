import math
from typing import List, Dict, Any, Optional
from backend.config import settings
from backend.database import get_supabase_admin
from backend.services.embedding_service import embedding_service
from backend.services.gemini_gateway import gemini_gateway

class RAGService:
    """
    Complete Retrieval-Augmented Generation (RAG) pipeline:
    1. Query embedding generation
    2. Vector similarity retrieval with user data isolation
    3. Grounded prompt synthesis
    4. Gemini API generation
    5. Source citation extraction
    """

    SYSTEM_PROMPT = (
        "You are DocuMind AI, an elite document intelligence assistant. "
        "Your task is to answer user questions with precision, clarity, and strict adherence to the provided document context.\n\n"
        "STRICT GROUNDING RULES:\n"
        "1. Base your answer EXCLUSIVELY on the retrieved document excerpts provided in the context.\n"
        "2. If the excerpts do not contain enough information to answer the question, explicitly state: "
        "'Based on your uploaded documents, I could not find information regarding this question.' Do NOT hallucinate, assume, or invent details.\n"
        "3. Provide inline citations citing the document name and page number, e.g. [Document.pdf, Page 2].\n"
        "4. Keep your answer professional, concise, structured, and easy to read with bullet points when applicable.\n"
        "5. RESPONSIBLE AI & UNCERTAINTY: Clearly distinguish verified facts found directly in the text from interpretations. If the document presents conflicting or ambiguous data, explicitly communicate the uncertainty to the user."
    )

    def __init__(self):
        self.embedding_service = embedding_service

    def retrieve_relevant_chunks(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        threshold: float = 0.05
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top_k most similar document chunks for the user.
        Tries Supabase pgvector RPC first; falls back to in-memory cosine similarity if RPC is unavailable.
        """
        query_vector = self.embedding_service.generate_embedding(query)
        admin = get_supabase_admin()

        # Method 1: Supabase pgvector RPC function
        try:
            rpc_res = admin.rpc(
                "match_document_chunks",
                {
                    "query_embedding": query_vector,
                    "match_threshold": threshold,
                    "match_count": top_k,
                    "filter_user_id": user_id
                }
            ).execute()

            if rpc_res.data and len(rpc_res.data) > 0:
                return rpc_res.data
        except Exception as e:
            print(f"[RAGService] RPC match_document_chunks error ({e}). Trying fallback query.")

        # Method 2: Python in-memory vector matching over user's chunks
        # Guarantees that vector search works even before Supabase RPC is executed
        try:
            chunks_res = admin.table("document_chunks") \
                .select("id, document_id, content, page_number, chunk_index, embedding") \
                .eq("user_id", user_id) \
                .execute()

            if not chunks_res.data:
                return []

            # Fetch document names
            doc_ids = list({c["document_id"] for c in chunks_res.data})
            docs_res = admin.table("documents").select("id, name").in_("id", doc_ids).execute()
            doc_name_map = {d["id"]: d["name"] for d in (docs_res.data or [])}

            scored_chunks = []
            for chunk in chunks_res.data:
                emb = chunk.get("embedding")
                if isinstance(emb, str):
                    import json
                    try:
                        emb = json.loads(emb)
                    except Exception:
                        continue
                if not emb or not isinstance(emb, list):
                    continue

                sim = self._cosine_similarity(query_vector, emb)
                if sim >= threshold:
                    scored_chunks.append({
                        "id": chunk["id"],
                        "document_id": chunk["document_id"],
                        "document_name": doc_name_map.get(chunk["document_id"], "Unknown Document"),
                        "content": chunk["content"],
                        "page_number": chunk.get("page_number", 1),
                        "chunk_index": chunk.get("chunk_index", 0),
                        "similarity": round(sim, 4)
                    })

            scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)
            return scored_chunks[:top_k]

        except Exception as e:
            print(f"[RAGService] Fallback vector retrieval error: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        if len(vec1) != len(vec2) or not vec1:
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def answer_question(
        self,
        question: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        gemini_api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end RAG answer generation.
        Returns:
        {
            "answer": str,
            "sources": List[Dict[str, Any]]
        }
        """
        # 1. Retrieve relevant chunks
        chunks = self.retrieve_relevant_chunks(question, user_id=user_id, top_k=5)

        # 2. Extract citations/sources
        sources = []
        context_blocks = []

        for i, c in enumerate(chunks, 1):
            doc_name = c.get("document_name", "Document")
            page_num = c.get("page_number", 1)
            content = c.get("content", "").strip()
            
            source_entry = {
                "document_id": c.get("document_id"),
                "document_name": doc_name,
                "page_number": page_num,
                "similarity": c.get("similarity", 0.0),
                "snippet": content[:250] + ("..." if len(content) > 250 else "")
            }
            # Deduplicate citations by doc + page
            if not any(s["document_name"] == doc_name and s["page_number"] == page_num for s in sources):
                sources.append(source_entry)

            context_blocks.append(
                f"[Source {i}: {doc_name} | Page {page_num}]\n{content}"
            )

        context_text = "\n\n---\n\n".join(context_blocks) if context_blocks else "No relevant document excerpts found."

        # 3. Format Conversation History
        history_text = ""
        if conversation_history:
            formatted_turns = []
            for msg in conversation_history[-6:]:  # last 6 messages
                role = "User" if msg.get("role") == "user" else "Assistant"
                formatted_turns.append(f"{role}: {msg.get('content', '')}")
            history_text = "\n".join(formatted_turns)

        # 4. Construct Prompt
        full_prompt = (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"=== RETRIEVED DOCUMENT CONTEXT ===\n"
            f"{context_text}\n\n"
        )
        if history_text:
            full_prompt += f"=== PREVIOUS CONVERSATION ===\n{history_text}\n\n"

        full_prompt += f"=== CURRENT QUESTION ===\nUser: {question}\n\nAssistant:"

        # 5. Determine Gemini API Key
        active_api_key = gemini_api_key or settings.GEMINI_API_KEY
        if not active_api_key:
            return {
                "answer": (
                    "**Gemini API Key Required**\n\n"
                    "The RAG retrieval successfully found the document context, but the backend requires a Gemini API key to generate answers. "
                    "Please configure `GEMINI_API_KEY` in your `.env` file or in the Settings tab."
                ),
                "sources": sources
            }

        # 6. Invoke Gemini API via Gateway
        try:
            answer = gemini_gateway.generate_text(
                prompt=full_prompt,
                system_instruction=self.SYSTEM_PROMPT,
                temperature=0.2,
                api_key=active_api_key
            )
            return {
                "answer": answer,
                "sources": sources
            }
        except Exception as e:
            err_str = str(e)
            if "API_KEY_INVALID" in err_str or "400" in err_str:
                msg = "The configured Gemini API key appears to be invalid. Please verify your API key in Settings or .env."
            elif "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                msg = "Gemini API rate limit exceeded. Please try again in a few moments or provide a different API key."
            else:
                msg = f"An error occurred while contacting the Gemini AI service: {err_str}"

            return {
                "answer": msg,
                "sources": sources
            }

rag_service = RAGService()
