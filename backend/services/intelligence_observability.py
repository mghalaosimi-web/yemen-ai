"""
backend/services/intelligence_observability.py
================================================
v10.2 Intelligence Observability & Operational Tracing Engine.

Records structured operational telemetry per turn without exposing
private internal prompt text or chain-of-thought dumps.
"""
from __future__ import annotations
import uuid
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from app.core.version import PIPELINE_VERSION, APP_VERSION


@dataclass
class StageTrace:
    name: str
    status: str       # 'completed', 'skipped', 'failed'
    duration_ms: float
    reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            'name': self.name,
            'status': self.status,
            'duration_ms': self.duration_ms,
        }
        if self.reason:
            d['reason'] = self.reason
        if self.details:
            d['details'] = self.details
        return d


@dataclass
class IntelligenceTrace:
    request_id: str
    conversation_id: str
    pipeline_version: str = PIPELINE_VERSION
    app_version: str = APP_VERSION
    stages: List[StageTrace] = field(default_factory=list)
    searched_sources: List[str] = field(default_factory=list)
    results_per_source: Dict[str, int] = field(default_factory=dict)
    evidence_count: int = 0
    retrieval_attempts: int = 1
    refinement_used: bool = False
    grounding_status: str = 'passed'
    response_quality: float = 1.0
    total_duration_ms: float = 0.0

    def add_stage(self, name: str, status: str, duration_ms: float, reason: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.stages.append(StageTrace(
            name=name,
            status=status,
            duration_ms=round(duration_ms, 2),
            reason=reason,
            details=details or {}
        ))

    def to_dict(self) -> Dict[str, Any]:
        return {
            'request_id': self.request_id,
            'conversation_id': self.conversation_id,
            'pipeline_version': self.pipeline_version,
            'app_version': self.app_version,
            'stages': [s.to_dict() for s in self.stages],
            'searched_sources': self.searched_sources,
            'results_per_source': self.results_per_source,
            'evidence_count': self.evidence_count,
            'retrieval_attempts': self.retrieval_attempts,
            'refinement_used': self.refinement_used,
            'grounding_status': self.grounding_status,
            'response_quality': self.response_quality,
            'total_duration_ms': round(self.total_duration_ms, 2),
        }


class IntelligenceObservability:
    """Telemetry collector for turn-level observability."""

    def create_trace(self, conversation_id: str) -> IntelligenceTrace:
        req_id = f"req_{uuid.uuid4().hex[:12]}"
        return IntelligenceTrace(
            request_id=req_id,
            conversation_id=conversation_id,
            pipeline_version=PIPELINE_VERSION,
            app_version=APP_VERSION
        )
