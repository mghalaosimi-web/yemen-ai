from __future__ import annotations
import math
import hashlib
import re
from collections import Counter
from typing import List, Dict, Any, Optional

DIM = 768

def _norm_hash(text: str) -> list[str]:
    t = str(text or '').lower()
    t = re.sub(r'[إأآا]', 'ا', t)
    t = t.replace('ى', 'ي').replace('ة', 'ه')
    t = re.sub(r'[ًٌٍَُِّْـ]', '', t)
    return re.findall(r'[\w\u0600-\u06ff]+', t)

def _features_hash(text: str) -> list[str]:
    words = _norm_hash(text)
    feats = []
    feats.extend('w:' + w for w in words)
    feats.extend('bg:' + a + '_' + b for a, b in zip(words, words[1:]))
    for w in words:
        z = '^' + w + '$'
        if len(w) >= 4:
            feats.extend('cg:' + z[i:i+3] for i in range(len(z) - 2))
    return feats

class EmbeddingProvider:
    """Abstract Base Class for Embedding Providers."""
    def embed(self, text: str) -> List[float]:
        raise NotImplementedError
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]

    @property
    def dimension(self) -> int:
        return DIM

    @property
    def provider_name(self) -> str:
        return "abstract_embedding_provider"

    def available(self) -> bool:
        return True

    def health(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "dimension": self.dimension,
            "available": self.available()
        }


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic, zero-dependency 768-dim Hash Embedding Provider."""
    def embed(self, text: str) -> List[float]:
        counts = Counter(_features_hash(text))
        vec = [0.0] * DIM
        for token, count in counts.items():
            h = int(hashlib.sha256(token.encode('utf-8')).hexdigest(), 16)
            idx = h % DIM
            sign = 1.0 if ((h >> 11) & 1) else -1.0
            vec[idx] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    @property
    def provider_name(self) -> str:
        return "hash_embedding"

    def available(self) -> bool:
        return True


class LocalSemanticEmbeddingProvider(EmbeddingProvider):
    """
    Optional Local Neural Semantic Embedding Provider.
    Auto-detects locally installed sentence-transformers / ONNX models without internet calls.
    """
    def __init__(self, model_name_or_path: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_path = model_name_or_path
        self._model = None
        self._is_available = False
        self._init_local_model()

    def _init_local_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            # Only load if local weights exist or sentence-transformers can load locally
            self._model = SentenceTransformer(self.model_path, local_files_only=True)
            self._is_available = True
        except Exception:
            self._model = None
            self._is_available = False

    def available(self) -> bool:
        return self._is_available

    def embed(self, text: str) -> List[float]:
        if not self._is_available or self._model is None:
            raise RuntimeError("LocalSemanticEmbeddingProvider is unavailable")
        vec = self._model.encode(text, convert_to_numpy=True).tolist()
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    @property
    def provider_name(self) -> str:
        return "local_semantic_embedding"

    @property
    def dimension(self) -> int:
        if self._is_available and self._model is not None:
            return getattr(self._model, "get_sentence_embedding_dimension", lambda: DIM)()
        return DIM


class HybridEmbeddingProvider(EmbeddingProvider):
    """
    Combines Local Semantic Embeddings (if available) with Hash Embeddings.
    Gracefully degrades to Hash Embedding if local neural model is missing.
    """
    def __init__(self, local_semantic_provider: Optional[LocalSemanticEmbeddingProvider] = None):
        self.hash_provider = HashEmbeddingProvider()
        self.semantic_provider = local_semantic_provider or LocalSemanticEmbeddingProvider()

    def available(self) -> bool:
        return True

    def embed(self, text: str) -> List[float]:
        # Always compute hash embedding to maintain backward compatibility
        hash_vec = self.hash_provider.embed(text)
        if self.semantic_provider.available():
            try:
                sem_vec = self.semantic_provider.embed(text)
                # Pad/truncate or combine if dimensions match
                if len(sem_vec) == len(hash_vec):
                    combined = [0.6 * s + 0.4 * h for s, h in zip(sem_vec, hash_vec)]
                    norm = math.sqrt(sum(v * v for v in combined)) or 1.0
                    return [v / norm for v in combined]
            except Exception:
                pass
        return hash_vec

    @property
    def provider_name(self) -> str:
        if self.semantic_provider.available():
            return "hybrid_semantic_hash"
        return "hash_embedding_fallback"

    def health(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "semantic_available": self.semantic_provider.available(),
            "hash_available": True,
            "dimension": self.dimension
        }


# Singleton factory instance
_provider_instance: Optional[EmbeddingProvider] = None

def get_embedding_provider() -> EmbeddingProvider:
    global _provider_instance
    if _provider_instance is None:
        semantic = LocalSemanticEmbeddingProvider()
        _provider_instance = HybridEmbeddingProvider(local_semantic_provider=semantic)
    return _provider_instance
