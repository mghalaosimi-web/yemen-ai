from __future__ import annotations
import math
from backend.rag.embedding_provider import get_embedding_provider, DIM

def embed_text(text: str) -> list[float]:
    return get_embedding_provider().embed(text)

def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))
