from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class RetrievalConfig:
    semantic_weight: float = 0.35
    lexical_weight: float = 0.25
    graph_weight: float = 0.15
    memory_weight: float = 0.10
    context_weight: float = 0.10
    source_quality_weight: float = 0.05
    recency_weight: float = 0.00
    duplicate_penalty: float = 0.15

    def to_dict(self) -> Dict[str, float]:
        return {
            "semantic_weight": self.semantic_weight,
            "lexical_weight": self.lexical_weight,
            "graph_weight": self.graph_weight,
            "memory_weight": self.memory_weight,
            "context_weight": self.context_weight,
            "source_quality_weight": self.source_quality_weight,
            "recency_weight": self.recency_weight,
            "duplicate_penalty": self.duplicate_penalty,
        }


@dataclass
class EvidenceScore:
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    graph_score: float = 0.0
    memory_score: float = 0.0
    context_score: float = 0.0
    source_quality_score: float = 0.8
    recency_score: float = 0.0
    duplicate_penalty: float = 0.0
    final_score: float = 0.0

    def compute_final(self, config: RetrievalConfig) -> float:
        score = (
            self.semantic_score * config.semantic_weight +
            self.lexical_score * config.lexical_weight +
            self.graph_score * config.graph_weight +
            self.memory_score * config.memory_weight +
            self.context_score * config.context_weight +
            self.source_quality_score * config.source_quality_weight +
            self.recency_score * config.recency_weight -
            self.duplicate_penalty * config.duplicate_penalty
        )
        self.final_score = max(0.0, min(1.0, round(score, 4)))
        return self.final_score

    def to_dict(self) -> Dict[str, float]:
        return {
            "semantic_score": round(self.semantic_score, 4),
            "lexical_score": round(self.lexical_score, 4),
            "graph_score": round(self.graph_score, 4),
            "memory_score": round(self.memory_score, 4),
            "context_score": round(self.context_score, 4),
            "source_quality_score": round(self.source_quality_score, 4),
            "recency_score": round(self.recency_score, 4),
            "duplicate_penalty": round(self.duplicate_penalty, 4),
            "final_score": round(self.final_score, 4),
        }

DEFAULT_RETRIEVAL_CONFIG = RetrievalConfig()
