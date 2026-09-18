"""
backend/services/mismatch_detector.py
======================================
v10.2 Answer-Knowledge Mismatch Detector & Abstention Validator.

Prevents false "I don't know" abstention responses when sufficient local
evidence was retrieved and available to the generator.
"""
from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple


class AnswerKnowledgeMismatchDetector:
    """Detects and repairs false abstention responses when evidence is available."""

    ABSTENTION_PATTERNS = [
        r'\b(لا أملك أدلة محلية|لا أعرف|لا يوجد معلومات|ليس لدي علم|لا أستطيع الإجابة)\b',
        r'\b(i don\'t know|no local evidence|insufficient evidence|cannot answer)\b'
    ]

    def detect_and_repair(
        self,
        answer: str,
        hits: List[Dict[str, Any]],
        requires_retrieval: bool,
        is_document_active: bool = False
    ) -> Tuple[str, bool, str]:
        """
        Returns (repaired_answer, mismatch_detected, evidence_state).
        """
        if not hits:
            return answer, False, 'NO_MATCHING_EVIDENCE'

        top_score = float(hits[0].get('hybrid_score', 0.0))
        is_abstention = any(re.search(pat, answer.lower()) for pat in self.ABSTENTION_PATTERNS)

        if top_score >= 0.75:
            state = 'SUFFICIENT_EVIDENCE'
        elif top_score >= 0.40:
            state = 'PARTIAL_EVIDENCE'
        else:
            state = 'WEAK_EVIDENCE'

        # If we have strong or partial evidence, but generator emitted abstention without active document strict failure
        if is_abstention and top_score >= 0.50 and not is_document_active:
            # Repair answer by synthesizing top evidence snippets directly
            top_texts = [h.get('text', '').strip() for h in hits[:3] if h.get('text')]
            repaired = f"بناءً على الأدلة المحلية المتوفرة:\n\n- " + "\n- ".join(top_texts)
            return repaired, True, state

        return answer, False, state
