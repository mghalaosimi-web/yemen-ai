from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from backend.services.arabic_normalizer import ArabicNormalizer

@dataclass
class GroundedClaim:
    claim_text: str
    status: str  # 'supported', 'weakly_supported', 'unsupported', 'conflicted'
    confidence: float
    evidence_ids: List[str] = field(default_factory=list)
    source_type: str = "knowledge"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_text": self.claim_text,
            "status": self.status,
            "confidence": round(self.confidence, 2),
            "evidence_ids": self.evidence_ids,
            "source_type": self.source_type
        }


class ClaimGroundingEngine:
    """Claim-Level Verification & Evidence Grounding Engine."""

    ABSTAIN_DOCUMENT_MSG = "لم أجد داخل المستند المرفوع دليلاً كافيًا للإجابة عن هذا السؤال، لذلك سألتزم بالمستند ولن أضيف معلومات من خارجه."

    def __init__(self):
        self.normalizer = ArabicNormalizer()

    def extract_claims(self, text: str) -> List[str]:
        raw_sentences = re.split(r'(?<=[.!؟?\n])\s+', text or '')
        claims = []
        for s in raw_sentences:
            s_clean = s.strip()
            if len(s_clean) >= 15:
                claims.append(s_clean)
        return claims or ([text.strip()] if text and len(text.strip()) >= 5 else [])

    def verify_and_ground(
        self,
        draft_answer: str,
        evidence_hits: List[Dict[str, Any]],
        is_document_active: bool = False,
        active_document_id: Optional[str] = None
    ) -> tuple[str, List[GroundedClaim], Dict[str, Any]]:
        
        # 1. Strict Document Mode Abstention Check
        if is_document_active:
            # Filter hits that strictly belong to active document
            doc_hits = [
                h for h in evidence_hits
                if active_document_id is None or str(h.get('metadata', {}).get('document_id')) == str(active_document_id)
            ]
            if not doc_hits:
                return (
                    self.ABSTAIN_DOCUMENT_MSG,
                    [GroundedClaim(claim_text=self.ABSTAIN_DOCUMENT_MSG, status='unsupported', confidence=0.0)],
                    {'grounded_claims': 0, 'unsupported_claims': 1, 'abstained': True}
                )

        claims = self.extract_claims(draft_answer)
        grounded_claims: List[GroundedClaim] = []
        verified_sentences: List[str] = []

        all_evidence_tokens = []
        for h in evidence_hits:
            ev_text = h.get('text', '')
            tokens = set(self.normalizer.normalize(ev_text).search_tokens)
            all_evidence_tokens.append((tokens, h.get('id') or h.get('metadata', {}).get('knowledge_id', 'doc_chunk')))

        unsupported_count = 0

        for claim in claims:
            c_tokens = set(self.normalizer.normalize(claim).search_tokens)
            if not c_tokens:
                verified_sentences.append(claim)
                continue

            max_overlap = 0.0
            matched_evidence_ids = []

            for ev_tokens, ev_id in all_evidence_tokens:
                overlap = len(c_tokens & ev_tokens) / max(1, len(c_tokens))
                if overlap > max_overlap:
                    max_overlap = overlap
                    matched_evidence_ids = [str(ev_id)]

            if max_overlap >= 0.45:
                status = 'supported'
                confidence = min(0.98, max_overlap)
                verified_sentences.append(claim)
            elif max_overlap >= 0.20:
                status = 'weakly_supported'
                confidence = max_overlap
                verified_sentences.append(claim)
            else:
                status = 'unsupported'
                confidence = max_overlap
                unsupported_count += 1
                if is_document_active:
                    # In document mode, strictly drop unsupported factual assertions
                    continue
                else:
                    verified_sentences.append(claim)

            grounded_claims.append(GroundedClaim(
                claim_text=claim,
                status=status,
                confidence=confidence,
                evidence_ids=matched_evidence_ids
            ))

        final_answer = " ".join(verified_sentences).strip() or draft_answer

        stats = {
            'claim_count': len(claims),
            'grounded_claims': len([c for c in grounded_claims if c.status in {'supported', 'weakly_supported'}]),
            'unsupported_claims': unsupported_count,
            'abstained': False
        }

        return final_answer, grounded_claims, stats
