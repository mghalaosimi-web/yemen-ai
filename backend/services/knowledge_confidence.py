from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class KnowledgeConfidenceProfile:
    source_confidence: float = 0.85
    retrieval_confidence: float = 0.50
    training_confidence: float = 0.80
    evidence_count: int = 0
    conflict_penalty: float = 0.0
    knowledge_confidence: float = 0.50

    def compute(
        self,
        retrieval_score: float,
        hits: List[Dict[str, Any]],
        has_conflict: bool = False
    ) -> float:
        self.evidence_count = len(hits)
        self.retrieval_confidence = min(1.0, max(0.0, retrieval_score))
        self.conflict_penalty = 0.30 if has_conflict else 0.0

        count_factor = min(1.0, self.evidence_count * 0.25)

        score = (
            self.retrieval_confidence * 0.45 +
            self.source_confidence * 0.25 +
            self.training_confidence * 0.15 +
            count_factor * 0.15 -
            self.conflict_penalty
        )
        self.knowledge_confidence = max(0.05, min(0.98, round(score, 4)))
        return self.knowledge_confidence

    def to_dict(self) -> Dict[str, float]:
        return {
            "source_confidence": round(self.source_confidence, 2),
            "retrieval_confidence": round(self.retrieval_confidence, 2),
            "training_confidence": round(self.training_confidence, 2),
            "evidence_count": self.evidence_count,
            "conflict_penalty": round(self.conflict_penalty, 2),
            "knowledge_confidence": round(self.knowledge_confidence, 2)
        }
