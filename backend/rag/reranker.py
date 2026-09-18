from __future__ import annotations
import math
import re
from typing import List, Dict, Any, Optional
from backend.services.arabic_normalizer import ArabicNormalizer

class Reranker:
    """Abstract Reranker Interface."""
    def rerank(self, query: str, candidates: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @property
    def provider_name(self) -> str:
        return "abstract_reranker"


class HeuristicReranker(Reranker):
    """
    Always available, zero-dependency offline Heuristic Reranker.
    Uses phrase alignment, query coverage, evidence density, and source metadata.
    """
    def __init__(self):
        self.normalizer = ArabicNormalizer()

    def rerank(self, query: str, candidates: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        q_norm = self.normalizer.normalize(query)
        q_tokens = set(q_norm.search_tokens)

        scored = []
        for idx, item in enumerate(candidates):
            text = item.get('text', '')
            t_norm = self.normalizer.normalize(text)
            t_tokens = set(t_norm.search_tokens)

            # Coverage & Overlap
            common = q_tokens & t_tokens
            coverage = len(common) / max(1, len(q_tokens)) if q_tokens else 0.0

            # Phrase Match Boost
            phrase_boost = 0.20 if q_norm.normalized_text in t_norm.normalized_text else 0.0

            # Density
            density = min(1.0, len(text) / 300.0)

            # Base score from candidate
            base_score = float(item.get('score', item.get('final_score', 0.5)))

            rerank_score = 0.40 * base_score + 0.35 * coverage + 0.15 * phrase_boost + 0.10 * density

            enriched_item = dict(item)
            enriched_item['original_rank'] = idx + 1
            enriched_item['reranker_score'] = round(rerank_score, 4)
            enriched_item['reranker_provider'] = self.provider_name
            scored.append((rerank_score, enriched_item))

        scored.sort(key=lambda x: x[0], reverse=True)

        reranked_results = []
        for new_idx, (score, item) in enumerate(scored[:limit]):
            item['reranked_rank'] = new_idx + 1
            item['score'] = max(item.get('score', 0.0), round(score, 4))
            reranked_results.append(item)

        return reranked_results

    @property
    def provider_name(self) -> str:
        return "heuristic_reranker"


class OptionalLocalCrossEncoderReranker(Reranker):
    """
    Optional Local Cross-Encoder Reranker.
    Auto-detects local sentence-transformers CrossEncoder without internet access.
    """
    def __init__(self, model_name_or_path: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_path = model_name_or_path
        self._encoder = None
        self._is_available = False
        self._fallback_reranker = HeuristicReranker()
        self._init_encoder()

    def _init_encoder(self):
        try:
            from sentence_transformers import CrossEncoder
            self._encoder = CrossEncoder(self.model_path, local_files_only=True)
            self._is_available = True
        except Exception:
            self._encoder = None
            self._is_available = False

    def rerank(self, query: str, candidates: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        if not self._is_available or self._encoder is None:
            return self._fallback_reranker.rerank(query, candidates, limit=limit)

        try:
            pairs = [[query, item.get('text', '')] for item in candidates]
            scores = self._encoder.predict(pairs)

            scored = []
            for idx, (score, item) in enumerate(zip(scores, candidates)):
                sigmoid_score = 1.0 / (1.0 + math.exp(-float(score)))
                enriched = dict(item)
                enriched['original_rank'] = idx + 1
                enriched['reranker_score'] = round(sigmoid_score, 4)
                enriched['reranker_provider'] = self.provider_name
                scored.append((sigmoid_score, enriched))

            scored.sort(key=lambda x: x[0], reverse=True)

            results = []
            for new_idx, (score, item) in enumerate(scored[:limit]):
                item['reranked_rank'] = new_idx + 1
                item['score'] = round(score, 4)
                results.append(item)

            return results
        except Exception:
            return self._fallback_reranker.rerank(query, candidates, limit=limit)

    @property
    def provider_name(self) -> str:
        if self._is_available:
            return "local_cross_encoder"
        return "heuristic_reranker_fallback"


def get_default_reranker() -> Reranker:
    return OptionalLocalCrossEncoderReranker()
