import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class KnowledgeQualityResult:
    valid: bool
    score: float
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    language: str = "en"
    encoding_valid: bool = True
    provenance_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "score": round(self.score, 2),
            "issues": self.issues,
            "warnings": self.warnings,
            "language": self.language,
            "encoding_valid": self.encoding_valid,
            "provenance_valid": self.provenance_valid
        }


class KnowledgeQualityValidator:
    def __init__(self, policy: str = "warn"):
        self.policy = policy  # reject, warn, allow

    def validate_item(
        self,
        content: str,
        title: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        provenance: Optional[Dict[str, Any]] = None
    ) -> KnowledgeQualityResult:
        metadata = metadata or {}
        provenance = provenance or metadata.get("provenance") or {}

        issues = []
        warnings = []
        score = 1.0

        # 1. Empty content check
        if not content or not content.strip():
            issues.append("Content is empty or whitespace only.")
            score -= 0.5

        # 3. Encoding validation
        encoding_valid = True
        try:
            content.encode("utf-8")
        except UnicodeEncodeError:
            encoding_valid = False
            issues.append("Invalid or corrupted character encoding detected.")
            score -= 0.3

        # 4. Language detection
        has_ar = bool(re.search(r"[\u0600-\u06FF]", content))
        has_en = bool(re.search(r"[a-zA-Z]", content))
        detected_lang = "ar" if has_ar and not has_en else ("mixed" if has_ar and has_en else "en")

        # 5 & 6. Extremely short / long chunks
        char_len = len(content.strip())
        if char_len < 15:
            warnings.append(f"Content chunk is extremely short ({char_len} chars).")
            score -= 0.1
        elif char_len > 10000:
            warnings.append(f"Content chunk is extremely long ({char_len} chars).")
            score -= 0.1

        # 7. Missing provenance
        provenance_valid = True
        source_id = metadata.get("source") or metadata.get("source_id") or provenance.get("source_id") or metadata.get("file_path")
        if not source_id and not metadata.get("document_id"):
            provenance_valid = False
            warnings.append("Missing explicit source provenance metadata.")
            score -= 0.15

        # 10. Translation mismatch / gibberish check
        if "???" in content or "\ufffd" in content:
            issues.append("Corrupted replacement symbols found in text.")
            score -= 0.3

        score = max(0.0, score)
        valid = (score >= 0.5 and len(issues) == 0) if self.policy == "reject" else (score >= 0.3)

        return KnowledgeQualityResult(
            valid=valid,
            score=score,
            issues=issues,
            warnings=warnings,
            language=detected_lang,
            encoding_valid=encoding_valid,
            provenance_valid=provenance_valid
        )
