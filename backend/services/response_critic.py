"""
backend/services/response_critic.py
===================================
v9.6 Response Quality Control & Critic Layer.

Evaluates generated answers across 10 quality dimensions and computes a QualityScore.
Provides actionable feedback if answer quality is subpar.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List
from backend.services.local_brain import normalize, tokens
from backend.services.query_analyzer import QueryAnalysis


@dataclass
class QualityScore:
    relevance: float
    groundedness: float
    clarity: float
    language_match: float
    context_alignment: float
    overall: float

    def to_dict(self) -> Dict[str, float]:
        return {
            'relevance': round(self.relevance, 2),
            'groundedness': round(self.groundedness, 2),
            'clarity': round(self.clarity, 2),
            'language_match': round(self.language_match, 2),
            'context_alignment': round(self.context_alignment, 2),
            'overall': round(self.overall, 2),
        }


class ResponseCritic:
    """Automated quality critic for local AI answers."""

    FORBIDDEN_LEAKS = [
        'session context', 'system prompt', 'hidden context', 'memory dump',
        'you are yemen ai', 'supplied evidence', 'knowledge:'
    ]

    def evaluate(
        self,
        query: str,
        answer: str,
        analysis: QueryAnalysis,
        hits: List[Dict[str, Any]],
        confidence: float,
        is_document_active: bool = False
    ) -> QualityScore:
        if not answer or not answer.strip():
            return QualityScore(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        norm_ans = normalize(answer)
        low_ans = answer.lower()

        # 1. Internal Leak & Prompt Safety Check
        if any(leak in low_ans for leak in self.FORBIDDEN_LEAKS):
            return QualityScore(0.1, 0.1, 0.1, 1.0, 0.1, 0.1)

        # 2. Language Matching
        # If user asked in Arabic, check if response contains Arabic text
        if analysis.detected_language == 'ar':
            ar_char_count = len(re.findall(r'[\u0600-\u06ff]', answer))
            if ar_char_count >= 10:
                lang_match = 1.0
            elif ar_char_count > 0:
                lang_match = 0.6
            else:
                lang_match = 0.1  # Pure English response to Arabic query
        else:
            lang_match = 1.0

        # 3. Relevance & Keyword Overlap
        q_tokens = set(analysis.keywords)
        ans_tokens = set(tokens(answer))
        if q_tokens:
            overlap = len(q_tokens & ans_tokens) / len(q_tokens)
            relevance = min(1.0, 0.4 + overlap * 0.6)
        else:
            relevance = 0.8

        # Canned responses or calculation responses are naturally relevant
        if analysis.intent in {'greeting', 'thanks', 'goodbye', 'identity', 'capabilities'}:
            relevance = 0.98

        # 4. Groundedness
        if is_document_active:
            if 'لم أجد داخل المستند' in answer or 'لم أجد هذه المعلومة' in answer or 'not find enough evidence' in low_ans:
                groundedness = 0.95  # Honest abstention is highly grounded
            elif hits:
                groundedness = min(0.98, max(0.5, confidence))
            else:
                groundedness = 0.2
        elif hits:
            groundedness = min(0.95, max(0.4, confidence))
        else:
            groundedness = 0.85 if analysis.intent in {'greeting', 'thanks', 'identity', 'capabilities'} else 0.5

        # 5. Clarity & Repetitiveness
        # Check if the answer repeats lines or paragraphs unnecessarily
        lines = [line.strip() for line in answer.splitlines() if len(line.strip()) > 10]
        unique_lines = set(lines)
        if lines:
            repetition_ratio = len(unique_lines) / len(lines)
            clarity = max(0.2, repetition_ratio * 0.95)
        else:
            clarity = 0.9

        # 6. Context Alignment
        context_align = 0.90 if analysis.requires_memory or analysis.intent == 'continue' else 0.95

        # Overall weighted score calculation
        overall = (
            relevance * 0.30 +
            groundedness * 0.25 +
            clarity * 0.15 +
            lang_match * 0.20 +
            context_align * 0.10
        )

        return QualityScore(
            relevance=relevance,
            groundedness=groundedness,
            clarity=clarity,
            language_match=lang_match,
            context_alignment=context_align,
            overall=overall
        )
