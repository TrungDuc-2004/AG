from functools import lru_cache
import math

from sentence_transformers import SentenceTransformer
from app.core.config import settings


@lru_cache(maxsize=1)
def _load_e5_model() -> SentenceTransformer:
    """
    Load E5 embedding model once per process.

    Default model: intfloat/multilingual-e5-base
    Vector dimension: 768
    First run will download the model from Hugging Face into local cache.
    """
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def e5_embed_query(text: str) -> list[float]:
    """Embed user query with E5 query prefix."""
    model = _load_e5_model()
    value = f"query: {text or ''}"
    embedding = model.encode(value, normalize_embeddings=True)
    return embedding.tolist()


def e5_embed_passage(text: str) -> list[float]:
    """Embed indexed passage/search bag text with E5 passage prefix."""
    model = _load_e5_model()
    value = f"passage: {text or ''}"
    embedding = model.encode(value, normalize_embeddings=True)
    return embedding.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(float(a[i]) * float(b[i]) for i in range(n))
    norm_a = math.sqrt(sum(float(a[i]) * float(a[i]) for i in range(n)))
    norm_b = math.sqrt(sum(float(b[i]) * float(b[i]) for i in range(n)))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
