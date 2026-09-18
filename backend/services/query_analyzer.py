"""
backend/services/query_analyzer.py
===================================
v9.6 Arabic-First Intent & Query Analysis Layer.

Analyzes raw user queries deeply beyond simple keyword matching.
Supports Modern Standard Arabic (MSA), common dialects (Yemeni, Egyptian, Gulf, etc.),
and English queries.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any
from backend.services.local_brain import normalize, tokens, AR_STOP

YEMENI_DIALECT_PATTERNS = [
    r'(?:^|\s)وش(?:$|\s)', r'(?:^|\s)ايش(?:$|\s)', r'(?:^|\s)ليش(?:$|\s)', r'(?:^|\s)كيفاش(?:$|\s)',
    r'(?:^|\s)ابغى(?:$|\s)', r'(?:^|\s)ابي(?:$|\s)', r'(?:^|\s)مابي(?:$|\s)', r'(?:^|\s)ذلحين(?:$|\s)',
    r'(?:^|\s)الحين(?:$|\s)', r'(?:^|\s)هاذا(?:$|\s)', r'(?:^|\s)هاذه(?:$|\s)', r'(?:^|\s)اشرحلي(?:$|\s)',
    r'(?:^|\s)قللي(?:$|\s)', r'وش تسوي', r'ايش تقدر', r'ايش قصده', r'وش يعني', r'ليش حصل', r'(?:^|\s)كمل(?:$|\s)'
]

GULF_EGYPTIAN_DIALECT_PATTERNS = [
    r'(?:^|\s)شنو(?:$|\s)', r'(?:^|\s)شلون(?:$|\s)', r'(?:^|\s)ازاي(?:$|\s)', r'(?:^|\s)عايز(?:$|\s)',
    r'(?:^|\s)دي(?:$|\s)', r'(?:^|\s)ده(?:$|\s)', r'(?:^|\s)ايه(?:$|\s)'
]


@dataclass
class QueryAnalysis:
    original_query: str
    normalized_query: str
    detected_language: str  # 'ar' or 'en'
    dialect: str            # 'yemeni', 'gulf_egyptian', 'msa', 'english'
    intent: str             # 'greeting', 'identity', 'explain', 'define', 'compare', 'steps', 'why', 'how', 'summarize', 'continue', 'verification', 'error_inquiry', 'document_grounded', 'question'
    secondary_intents: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    question_type: str = 'general'  # 'factual', 'conceptual', 'procedural', 'comparative', 'causal', 'evaluative', 'continuation'
    temporal_reference: str = 'none' # 'past', 'present', 'future', 'sequential', 'none'
    reference_terms: List[str] = field(default_factory=list) # e.g. 'هذا', 'المستند', 'الملف', 'قبل'
    ambiguity_score: float = 0.0
    complexity_score: float = 0.5
    required_answer_style: str = 'direct' # 'direct', 'explanation', 'summary', 'steps', 'comparison', 'causal', 'structured'
    requires_retrieval: bool = True
    requires_memory: bool = False
    requires_document_grounding: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_query': self.original_query,
            'normalized_query': self.normalized_query,
            'detected_language': self.detected_language,
            'dialect': self.dialect,
            'intent': self.intent,
            'secondary_intents': self.secondary_intents,
            'entities': self.entities,
            'concepts': self.concepts,
            'keywords': self.keywords,
            'question_type': self.question_type,
            'temporal_reference': self.temporal_reference,
            'reference_terms': self.reference_terms,
            'ambiguity_score': self.ambiguity_score,
            'complexity_score': self.complexity_score,
            'required_answer_style': self.required_answer_style,
            'requires_retrieval': self.requires_retrieval,
            'requires_memory': self.requires_memory,
            'requires_document_grounding': self.requires_document_grounding,
        }


class QueryAnalyzer:
    """Arabic-first query analyzer."""

    REFERENTIAL_PATTERNS = [
        (r'\b(هذا|هذه|ذلك|تلك|هذي|هاذا|هذين|هؤلاء)\b', 'demonstrative'),
        (r'\b(الملف|المستند|الورقه|التقرير)\b', 'document_ref'),
        (r'\b(قصده|يقصد|معناه|معناها|معنى)\b', 'meaning_ref'),
        (r'\b(السابق|قبل|الماضي|الذي قلته|اللي قلته)\b', 'prior_ref'),
        (r'\b(كمل|تابع|واصل|استمر|زاد|اكمل)\b', 'continuation_ref'),
        (r'\b(بينهم|بينهما|بين الاثنين)\b', 'comparison_ref'),
        (r'\b(صحيح|صح|خطا|خطأ|غير صحيح)\b', 'verification_ref'),
    ]

    INTENT_MAP = [
        ('greeting', [r'\b(مرحبا|اهلا|السلام عليكم|هلا|صباح الخير|مساء الخير|اهلين|hello|hi|hey)\b']),
        ('identity', [r'\b(من انت|عرفني بنفسك|ما انت|اسمك ايش|اسمك ماذا|مين انت|who are you|what is your name)\b']),
        ('thanks', [r'\b(شكرا|مشكور|تسلم|جزاك الله خير|thanks|thank you)\b']),
        ('goodbye', [r'\b(وداعا|مع السلامه|باي|bye|الى اللقاء|goodbye)\b']),
        ('capabilities', [r'\b(ماذا تستطيع|ماذا تقدر|ايش تقدر|قدراتك|ماذا تفعل|وش تسوي|ايش تسوي|what can you do)\b']),
        ('continue', [r'\b(كمل|تابع|واصل|استمر|نعم كمل|اكمل|شرح لي من البدايه|وضح اكثر|فصل اكثر|continue|go on)\b']),
        ('verification', [r'\b(هل هذا صحيح|هل صح|هل المعلومات صحيحه|صحيح ولا لا|وين الخطا|وين الخطأ|is this correct|is it true)\b']),
        ('error_inquiry', [r'\b(وين الخطا|وين الخطأ|لماذا فشل|ما السبب في الخطأ|خطأ في الكود|error|bug|issue)\b']),
        ('summarize', [r'\b(لخص|اختصر|ملخص|الخلاصه|موجز|اعطني المهم|المهم|summarize|summary)\b']),
        ('compare', [r'\b(قارن|الفرق بين|مقارنه|مقارنة|وش الفرق|ايش الفرق|قارن بينهم|compare|difference between)\b']),
        ('steps', [r'\b(خطوات|خطوه بخطوه|خطوة بخطوة|كيف ابدا|كيف ابدأ|من اين ابدا|الطريقه|steps|how to start)\b']),
        ('why', [r'\b(لماذا|ليش|السبب|لماذا يحدث|ليش حصل|ليش كذا|why|reason)\b']),
        ('how', [r'\b(كيف يعمل|كيف اشتغل|كيف يتم|كيف اسوي|كيف افعل|كيف يتعلم|شلون|how does|how to)\b']),
        ('define', [r'\b(ما هو|ماهو|ماهي|ما هي|تعريف|عرف لي|وش يعني|وش هو|ايش يعني|ماذا يعني|ما معنى|what is|what are|define|definition of)\b']),
        ('explain', [r'\b(وضح|اشرح|فصل|تفصيل|بالتفصيل|شرح|وضح لي|explain|elaborate)\b']),
    ]

    def detect_language(self, text: str) -> str:
        return 'ar' if re.search(r'[\u0600-\u06ff]', text or '') else 'en'

    def detect_dialect(self, text: str, lang: str) -> str:
        if lang != 'ar':
            return 'english'
        lower_raw = (text or '').lower()
        if any(re.search(p, lower_raw) for p in YEMENI_DIALECT_PATTERNS):
            return 'yemeni'
        if any(re.search(p, lower_raw) for p in GULF_EGYPTIAN_DIALECT_PATTERNS):
            return 'gulf_egyptian'
        return 'msa'

    def extract_reference_terms(self, text: str) -> List[str]:
        norm = normalize(text)
        refs = []
        for pat, ref_type in self.REFERENTIAL_PATTERNS:
            matches = re.findall(pat, norm)
            if matches:
                for m in matches:
                    if isinstance(m, tuple):
                        m = m[0]
                    if m not in refs:
                        refs.append(m)
        return refs

    def extract_keywords_and_concepts(self, text: str) -> tuple[List[str], List[str]]:
        kw = tokens(text)
        concepts = []
        norm = normalize(text)
        # Multi-word technical/domain phrases
        phrases = [
            'الذكاء الاصطناعي', 'تعلم الاله', 'تعلم الالة', 'التعلم الالي', 'تعلم الالي',
            'الأمن السيبراني', 'الامن السيبراني', 'قاعدة البيانات', 'قاعده البيانات',
            'معالجة اللغات الطبيعية', 'الشبكات العصبية', 'الاسترجاع المعزز', 'تطوير الويب',
            'تحليل البيانات', 'المنهج العلمي'
        ]
        for p in phrases:
            if normalize(p) in norm:
                concepts.append(p)
        
        # Single keywords over 3 chars
        for k in kw:
            if len(k) >= 4 and k not in concepts:
                concepts.append(k)
        
        return kw, list(dict.fromkeys(concepts))[:12]

    def analyze(self, query: str, active_document: str | None = None) -> QueryAnalysis:
        original = (query or '').strip()
        norm = normalize(original)
        lang = self.detect_language(original)
        dialect = self.detect_dialect(original, lang)
        
        # Primary & secondary intent matching
        primary_intent = 'question'
        secondary_intents = []

        for intent_name, patterns in self.INTENT_MAP:
            for pat in patterns:
                if re.search(pat, norm):
                    if primary_intent == 'question':
                        primary_intent = intent_name
                    elif intent_name not in secondary_intents and intent_name != primary_intent:
                        secondary_intents.append(intent_name)

        ref_terms = self.extract_reference_terms(original)
        kw, concepts = self.extract_keywords_and_concepts(original)

        # Question type & required answer style
        q_type = 'general'
        style = 'direct'

        if primary_intent == 'define':
            q_type = 'conceptual'
            style = 'definition'
        elif primary_intent == 'explain':
            q_type = 'conceptual'
            style = 'explanation'
        elif primary_intent == 'compare':
            q_type = 'comparative'
            style = 'comparison'
        elif primary_intent == 'steps':
            q_type = 'procedural'
            style = 'steps'
        elif primary_intent == 'why':
            q_type = 'causal'
            style = 'causal'
        elif primary_intent == 'summarize':
            q_type = 'conceptual'
            style = 'summary'
        elif primary_intent == 'verification':
            q_type = 'evaluative'
            style = 'structured'
        elif primary_intent == 'continue':
            q_type = 'continuation'
            style = 'explanation'

        # Document grounding flag
        req_doc = bool(active_document) or any(x in norm for x in ['الملف', 'المستند', 'التقرير', 'في المستند', 'من الملف'])

        # Retrieval requirement
        no_retrieval_intents = {'greeting', 'thanks', 'goodbye', 'identity', 'capabilities'}
        req_retrieval = primary_intent not in no_retrieval_intents

        # Memory requirement
        req_memory = len(ref_terms) > 0 or primary_intent == 'continue'

        # Ambiguity & Complexity scores
        tok_count = len(kw)
        ambiguity = 0.8 if tok_count <= 2 and primary_intent in {'question', 'continue'} else max(0.0, 0.5 - tok_count * 0.08)
        complexity = min(1.0, 0.3 + tok_count * 0.08 + (0.2 if primary_intent in {'compare', 'explain', 'steps'} else 0.0))

        return QueryAnalysis(
            original_query=original,
            normalized_query=norm,
            detected_language=lang,
            dialect=dialect,
            intent=primary_intent,
            secondary_intents=secondary_intents,
            entities=[],
            concepts=concepts,
            keywords=kw,
            question_type=q_type,
            temporal_reference='none',
            reference_terms=ref_terms,
            ambiguity_score=round(ambiguity, 2),
            complexity_score=round(complexity, 2),
            required_answer_style=style,
            requires_retrieval=req_retrieval,
            requires_memory=req_memory,
            requires_document_grounding=req_doc
        )
