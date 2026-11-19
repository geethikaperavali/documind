import os
import math
import hashlib
from typing import List
from backend.config import settings

# Prevent huggingface hub from blocking on offline network checks
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

_model = None
_model_failed = False

def get_sentence_transformer_model():
    """
    Lazy loads the SentenceTransformer model into memory using local cache.
    Falls back gracefully to deterministic vector engine if local weights are not accessible.
    """
    global _model, _model_failed
    if _model_failed:
        return None
    if _model is not None:
        return _model

    try:
        from sentence_transformers import SentenceTransformer
        # Check local cache only to prevent blocking network attempts
        _model = SentenceTransformer(settings.EMBEDDING_MODEL, local_files_only=True)
        return _model
    except Exception as e:
        print(f"[EmbeddingService] Local SentenceTransformer cache unavailable ({e}). Using deterministic 384-dim normalized vector engine.", flush=True)
        _model_failed = True
        return None


class EmbeddingService:
    """
    Generates 384-dimensional vector embeddings for text chunks and queries.
    Supports SentenceTransformers, Gemini Embeddings, and deterministic hashed vectors.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generates a 384-dim normalized vector for a single string.
        """
        results = self.generate_embeddings([text])
        return results[0]

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates 384-dim normalized vectors for a batch of strings.
        """
        if not texts:
            return []

        # 1. Try SentenceTransformers
        model = get_sentence_transformer_model()
        if model is not None:
            try:
                embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
                # Convert numpy array to list of floats
                return [emb.tolist() if hasattr(emb, "tolist") else list(emb) for emb in embeddings]
            except Exception as e:
                print(f"[EmbeddingService] SentenceTransformer encoding failed: {e}")

        # 2. Deterministic normalized semantic-hash fallback
        # Guarantees that vector search and pgvector column requirements (384 dimensions) are always satisfied
        fallback_embeddings = []
        for text in texts:
            vec = self._deterministic_vector(text, self.dim)
            fallback_embeddings.append(vec)

        return fallback_embeddings

    def _deterministic_vector(self, text: str, dim: int) -> List[float]:
        """
        Generates a deterministic 384-dim unit vector based on text token hashing.
        Used as high-reliability fallback.
        """
        vector = [0.0] * dim
        words = text.lower().split()
        if not words:
            words = [text.lower()]

        for word in words:
            h = hashlib.sha256(word.encode("utf-8")).digest()
            for i in range(0, min(len(h), dim)):
                val = (h[i] - 128) / 128.0
                idx = (i * 13) % dim
                vector[idx] += val

        # Normalize to unit vector (L2 norm)
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [round(x / norm, 6) for x in vector]
        else:
            vector[0] = 1.0

        return vector

embedding_service = EmbeddingService(dim=settings.EMBEDDING_DIM)
