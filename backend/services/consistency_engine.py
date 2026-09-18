from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class ConflictReport:
    has_conflict: bool = False
    conflict_type: str = "none"  # 'numeric', 'date', 'negation', 'factual', 'none'
    conflicting_claims: List[Dict[str, Any]] = field(default_factory=list)
    conflict_severity: float = 0.0  # 0.0 to 1.0
    recommended_action: str = "proceed"  # 'proceed', 'prefer_high_confidence_source', 'mention_disagreement', 'ask_or_report_uncertainty'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_conflict": self.has_conflict,
            "conflict_type": self.conflict_type,
            "conflicting_claims": self.conflicting_claims,
            "conflict_severity": round(self.conflict_severity, 2),
            "recommended_action": self.recommended_action
        }


class EvidenceConsistencyAnalyzer:
    """Structured Evidence Contradiction & Consistency Engine."""

    NUMERIC_PAT = re.compile(r'(\b[\w\u0600-\u06ff\s]{2,20}\b)\s*[:=]?\s*(\d+)')
    DATE_PAT = re.compile(r'\b(19\d\d|20\d\d)\b')
    NEGATION_PAT = re.compile(r'\b(لا|ليس|غير|لم|لن|no|not|never)\b')

    def analyze(self, hits: List[Dict[str, Any]]) -> ConflictReport:
        if not hits or len(hits) < 2:
            return ConflictReport()

        conflicts = []

        # 1. Numeric Conflict Detection
        num_claims = {}
        for idx, item in enumerate(hits):
            text = item.get('text', '')
            for entity, val in self.NUMERIC_PAT.findall(text):
                ent_clean = entity.strip().lower()
                if len(ent_clean) >= 3:
                    if ent_clean in num_claims:
                        prev_val, prev_idx = num_claims[ent_clean]
                        if prev_val != val:
                            conflicts.append({
                                'type': 'numeric',
                                'entity': ent_clean,
                                'val_a': prev_val,
                                'source_a_index': prev_idx,
                                'val_b': val,
                                'source_b_index': idx,
                                'excerpt_a': hits[prev_idx].get('text', '')[:100],
                                'excerpt_b': text[:100]
                            })
                    else:
                        num_claims[ent_clean] = (val, idx)

        if conflicts:
            return ConflictReport(
                has_conflict=True,
                conflict_type="numeric",
                conflicting_claims=conflicts,
                conflict_severity=0.85,
                recommended_action="mention_disagreement"
            )

        # 2. Date Conflict Detection
        dates_found = []
        for idx, item in enumerate(hits):
            text = item.get('text', '')
            found = self.DATE_PAT.findall(text)
            if found:
                dates_found.append((set(found), idx, text))

        if len(dates_found) >= 2:
            for i in range(len(dates_found)):
                for j in range(i + 1, len(dates_found)):
                    dates1, idx1, t1 = dates_found[i]
                    dates2, idx2, t2 = dates_found[j]
                    if not (dates1 & dates2):
                        # Potential date discrepancy on same subject
                        conflicts.append({
                            'type': 'date',
                            'dates_a': list(dates1),
                            'dates_b': list(dates2),
                            'source_a_index': idx1,
                            'source_b_index': idx2,
                            'excerpt_a': t1[:100],
                            'excerpt_b': t2[:100]
                        })

        if conflicts:
            return ConflictReport(
                has_conflict=True,
                conflict_type="date",
                conflicting_claims=conflicts,
                conflict_severity=0.75,
                recommended_action="mention_disagreement"
            )

        return ConflictReport()
