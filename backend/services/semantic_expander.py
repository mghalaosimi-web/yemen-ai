from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any
from backend.services.arabic_normalizer import ArabicNormalizer

@dataclass
class ExpansionTerm:
    term: str
    category: str  # 'synonym', 'concept', 'entity_alias', 'morphology', 'dialect', 'english_tech'
    confidence: float  # 0.0 to 1.0
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'term': self.term,
            'category': self.category,
            'confidence': round(self.confidence, 2),
            'source': self.source
        }


class SemanticQueryExpander:
    """Controlled Semantic Query Expansion Engine."""

    DIALECT_MAP = {
        'ايش': ('ماذا', 'dialect', 0.95),
        'وش': ('ماذا', 'dialect', 0.95),
        'شلون': ('كيف', 'dialect', 0.95),
        'ازاي': ('كيف', 'dialect', 0.95),
        'ليش': ('لماذا', 'dialect', 0.95),
        'ابغى': ('اريد', 'dialect', 0.90),
        'ابي': ('اريد', 'dialect', 0.90),
        'عايز': ('اريد', 'dialect', 0.90),
        'ذلحين': ('الان', 'dialect', 0.95),
        'الحين': ('الان', 'dialect', 0.95),
        'شنو': ('ماذا', 'dialect', 0.90),
        'ايه': ('ماذا', 'dialect', 0.85),
    }

    SYNONYM_CONCEPT_MAP = {
        'ذكاء صناعي': [
            ExpansionTerm('الذكاء الاصطناعي', 'concept', 0.98, 'domain_dict'),
            ExpansionTerm('AI', 'english_tech', 0.95, 'domain_dict'),
            ExpansionTerm('Artificial Intelligence', 'english_tech', 0.95, 'domain_dict'),
            ExpansionTerm('تعلم الاله', 'synonym', 0.85, 'domain_dict'),
        ],
        'الذكاء الاصطناعي': [
            ExpansionTerm('AI', 'english_tech', 0.95, 'domain_dict'),
            ExpansionTerm('Artificial Intelligence', 'english_tech', 0.95, 'domain_dict'),
            ExpansionTerm('تعلم الاله', 'synonym', 0.85, 'domain_dict'),
            ExpansionTerm('الشبكات العصبية', 'concept', 0.80, 'domain_dict'),
        ],
        'كمبيوتر': [
            ExpansionTerm('حاسوب', 'synonym', 0.98, 'tech_dict'),
            ExpansionTerm('حاسب', 'synonym', 0.95, 'tech_dict'),
            ExpansionTerm('computer', 'english_tech', 0.95, 'tech_dict'),
        ],
        'حاسوب': [
            ExpansionTerm('كمبيوتر', 'synonym', 0.98, 'tech_dict'),
            ExpansionTerm('computer', 'english_tech', 0.95, 'tech_dict'),
        ],
        'قاعدة بيانات': [
            ExpansionTerm('قاعده البيانات', 'morphology', 0.98, 'tech_dict'),
            ExpansionTerm('database', 'english_tech', 0.95, 'tech_dict'),
            ExpansionTerm('SQL', 'english_tech', 0.80, 'tech_dict'),
        ],
        'برمجة': [
            ExpansionTerm('تطوير البرمجيات', 'concept', 0.90, 'tech_dict'),
            ExpansionTerm('programming', 'english_tech', 0.95, 'tech_dict'),
            ExpansionTerm('coding', 'english_tech', 0.90, 'tech_dict'),
        ],
        'امن سيبراني': [
            ExpansionTerm('الأمن السيبراني', 'concept', 0.98, 'tech_dict'),
            ExpansionTerm('cybersecurity', 'english_tech', 0.95, 'tech_dict'),
            ExpansionTerm('أمن المعلومات', 'synonym', 0.90, 'tech_dict'),
        ],
        'تعلم الاله': [
            ExpansionTerm('Machine Learning', 'english_tech', 0.95, 'tech_dict'),
            ExpansionTerm('ML', 'english_tech', 0.90, 'tech_dict'),
            ExpansionTerm('تدريب النموذج', 'concept', 0.85, 'tech_dict'),
        ]
    }

    def __init__(self):
        self.normalizer = ArabicNormalizer()

    def expand(self, query: str, min_confidence: float = 0.70) -> List[ExpansionTerm]:
        raw_norm = self.normalizer.normalize(query)
        norm_query = raw_norm.normalized_text

        expansions: List[ExpansionTerm] = []
        seen_terms = {norm_query, query.strip().lower()}

        # 1. Dialect replacements
        words = norm_query.split()
        for w in words:
            if w in self.DIALECT_MAP:
                msa_target, cat, conf = self.DIALECT_MAP[w]
                if msa_target not in seen_terms:
                    seen_terms.add(msa_target)
                    expansions.append(ExpansionTerm(term=msa_target, category=cat, confidence=conf, source='dialect_normalizer'))

        # 2. Concept / Synonym / English Tech mapping
        for key, terms in self.SYNONYM_CONCEPT_MAP.items():
            if key in norm_query or any(k in norm_query for k in key.split()):
                for exp in terms:
                    if exp.term.lower() not in seen_terms and exp.confidence >= min_confidence:
                        seen_terms.add(exp.term.lower())
                        expansions.append(exp)

        # 3. Light Stemming Variations
        for stem in raw_norm.light_stems:
            if stem not in seen_terms and len(stem) >= 3:
                seen_terms.add(stem)
                expansions.append(ExpansionTerm(term=stem, category='morphology', confidence=0.85, source='light_stemmer'))

        # Filter out expansions below min_confidence
        filtered = [e for e in expansions if e.confidence >= min_confidence]
        return filtered
