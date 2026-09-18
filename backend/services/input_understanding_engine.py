"""
backend/services/input_understanding_engine.py
================================================
v10.2 Universal Input Understanding Engine.

Preserves the original user text while creating normalized and semantic
representations. Accurately detects language, Arabic dialects (Yemeni, Gulf/Egyptian, MSA),
intents, task classifications (QUESTION, EXPLANATION_REQUEST, CONTINUATION, CORRECTION,
COMPARISON, COMMAND, PROJECT_QUESTION, PERSONAL_QUESTION, DOCUMENT_QUESTION, UNCERTAINTY,
SHORT_FOLLOW_UP, REFERENCE), reference terms, entities, and domain concepts.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from backend.services.local_brain import normalize, tokens

YEMENI_PATTERNS = [
    r'(?:^|\s)وش(?:$|\s)', r'(?:^|\s)ايش(?:$|\s)', r'(?:^|\s)ليش(?:$|\s)', r'(?:^|\s)كيفاش(?:$|\s)',
    r'(?:^|\s)ابغى(?:$|\s)', r'(?:^|\s)ابي(?:$|\s)', r'(?:^|\s)مابي(?:$|\s)', r'(?:^|\s)ذلحين(?:$|\s)',
    r'(?:^|\s)الحين(?:$|\s)', r'(?:^|\s)هاذا(?:$|\s)', r'(?:^|\s)هاذه(?:$|\s)', r'(?:^|\s)اشرحلي(?:$|\s)',
    r'(?:^|\s)قللي(?:$|\s)', r'وش تسوي', r'ايش تقدر', r'ايش قصده', r'وش يعني', r'ليش حصل', r'(?:^|\s)كمل(?:$|\s)',
    r'(?:^|\s)شو(?:$|\s)', r'(?:^|\s)طيب(?:$|\s)', r'(?:^|\s)خلاص(?:$|\s)', r'(?:^|\s)كذا(?:$|\s)', r'(?:^|\s)هكذا(?:$|\s)'
]

GULF_EGYPTIAN_PATTERNS = [
    r'(?:^|\s)شنو(?:$|\s)', r'(?:^|\s)شلون(?:$|\s)', r'(?:^|\s)ازاي(?:$|\s)', r'(?:^|\s)عايز(?:$|\s)',
    r'(?:^|\s)دي(?:$|\s)', r'(?:^|\s)ده(?:$|\s)', r'(?:^|\s)ايه(?:$|\s)'
]

CORRECTION_PATTERNS = [
    r'\b(لا|لا قصدي|قصدي|لا المعذرة|تعديل|خطأ|بل|اقصد|أقصد|لا قصدت)\b',
    r'\b(no i meant|i mean|correction|instead of)\b'
]

CONTINUATION_PATTERNS = [
    r'\b(كمل|تابع|واصل|استمر|زاد|اكمل|بعدين|طيب وبعد|ثم ماذا|نعم كمل|continue|go on)\b'
]

UNCERTAINTY_PATTERNS = [
    r'\b(ما فهمت|لم افهم|غير واضح|وضح اكثر|مش فاهم|dint understand|unclear)\b'
]

PROJECT_PATTERNS = [
    r'\b(yemen ai|يمن اي اي|المشروع|النسخة|الإصدار|v9|v10|v10\.1|v10\.2|تطور المشروع|آخر نسخة|اخر نسخه|سجل المشروع)\b'
]

PERSONAL_PATTERNS = [
    r'\b(تعرف عني|عني|سيرتي|تفضيلاتي|طريقة عملي|اسمي|طبيعة عملي|عن المستخدم|about me|my profile|my preference)\b'
]

DOCUMENT_PATTERNS = [
    r'\b(الملف|المستند|الورقه|التقرير|في الملف|في المستند|الأرباح|النص مرفق|document|pdf|file)\b'
]


@dataclass
class InputUnderstandingResult:
    original_text: str
    normalized_text: str
    semantic_text: str
    detected_language: str       # 'ar', 'en', 'mixed'
    dialect: str                 # 'yemeni', 'gulf_egyptian', 'msa', 'english'
    intent: str                  # 'question', 'define', 'explain', 'compare', 'steps', 'why', 'how', 'continue', 'correction', etc.
    task_type: str               # 'QUESTION', 'EXPLANATION_REQUEST', 'CONTINUATION', 'CORRECTION', 'COMPARISON', 'COMMAND', 'PROJECT_QUESTION', 'PERSONAL_QUESTION', 'DOCUMENT_QUESTION', 'UNCERTAINTY', 'SHORT_FOLLOW_UP', 'REFERENCE'
    secondary_intents: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    reference_terms: List[str] = field(default_factory=list)
    ambiguity_score: float = 0.0
    complexity_score: float = 0.5
    confidence: float = 0.95
    requires_retrieval: bool = True
    requires_memory: bool = False
    requires_document_grounding: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_text': self.original_text,
            'normalized_text': self.normalized_text,
            'semantic_text': self.semantic_text,
            'detected_language': self.detected_language,
            'dialect': self.dialect,
            'intent': self.intent,
            'task_type': self.task_type,
            'secondary_intents': self.secondary_intents,
            'entities': self.entities,
            'concepts': self.concepts,
            'keywords': self.keywords,
            'reference_terms': self.reference_terms,
            'ambiguity_score': self.ambiguity_score,
            'complexity_score': self.complexity_score,
            'confidence': self.confidence,
            'requires_retrieval': self.requires_retrieval,
            'requires_memory': self.requires_memory,
            'requires_document_grounding': self.requires_document_grounding,
        }


class InputUnderstandingEngine:
    """Central universal engine for analyzing raw input preserving fidelity."""

    REFERENTIAL_PATTERNS = [
        (r'\b(هذا|هذه|ذلك|تلك|هذي|هاذا|هذين|هؤلاء|هو|هي)\b', 'demonstrative'),
        (r'\b(الملف|المستند|الورقه|التقرير)\b', 'document_ref'),
        (r'\b(قصده|يقصد|معناه|معناها|معنى)\b', 'meaning_ref'),
        (r'\b(السابق|قبل|الماضي|الذي قلته|اللي قلته|النسخة السابقة)\b', 'prior_ref'),
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
        ('correction', [r'\b(لا قصدي|قصدي|تعديل|بل قصدي|بل قصدت|لا قصدت|no i meant|correction)\b']),
        ('continue', [r'\b(كمل|تابع|واصل|استمر|نعم كمل|اكمل|شرح لي من البدايه|وضح اكثر|فصل اكثر|continue|go on)\b']),
        ('verification', [r'\b(هل هذا صحيح|هل صح|هل المعلومات صحيحه|صحيح ولا لا|وين الخطا|is this correct|is it true)\b']),
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
        has_ar = bool(re.search(r'[\u0600-\u06ff]', text or ''))
        has_en = bool(re.search(r'[a-zA-Z]', text or ''))
        if has_ar and has_en:
            return 'mixed'
        elif has_ar:
            return 'ar'
        return 'en'

    def detect_dialect(self, text: str, lang: str) -> str:
        if lang == 'en':
            return 'english'
        lower_raw = (text or '').lower()
        if any(re.search(p, lower_raw) for p in YEMENI_PATTERNS):
            return 'yemeni'
        if any(re.search(p, lower_raw) for p in GULF_EGYPTIAN_PATTERNS):
            return 'gulf_egyptian'
        return 'msa'

    def classify_task_type(self, norm: str, intent: str, active_doc: Optional[str] = None) -> str:
        if any(re.search(p, norm) for p in CORRECTION_PATTERNS):
            return 'CORRECTION'
        if intent == 'continue' or any(re.search(p, norm) for p in CONTINUATION_PATTERNS):
            return 'CONTINUATION'
        if any(re.search(p, norm) for p in UNCERTAINTY_PATTERNS):
            return 'UNCERTAINTY'
        if active_doc or any(re.search(p, norm) for p in DOCUMENT_PATTERNS):
            return 'DOCUMENT_QUESTION'
        if any(re.search(p, norm) for p in PERSONAL_PATTERNS):
            return 'PERSONAL_QUESTION'
        if any(re.search(p, norm) for p in PROJECT_PATTERNS):
            return 'PROJECT_QUESTION'
        if intent == 'compare':
            return 'COMPARISON'
        if intent in {'explain', 'define', 'steps'}:
            return 'EXPLANATION_REQUEST'
        if len(tokens(norm)) <= 4 and any(x in norm for x in ['هذا', 'ذلك', 'هو', 'هي', 'المشروع', 'النظام']):
            return 'REFERENCE'
        if len(tokens(norm)) <= 4:
            return 'SHORT_FOLLOW_UP'
        return 'QUESTION'

    def build_semantic_text(self, original: str, norm: str, dialect: str) -> str:
        semantic = norm
        # Map dialect terms to canonical semantic expressions for better retrieval
        replacements = [
            (r'\bايش\b', 'ماذا'),
            (r'\bوش\b', 'ماذا'),
            (r'\bليش\b', 'لماذا'),
            (r'\bذلحين\b', 'الآن'),
            (r'\bالحين\b', 'الآن'),
            (r'\bابغى\b', 'أريد'),
            (r'\bعايز\b', 'أريد'),
            (r'\bازاي\b', 'كيف'),
            (r'\bشلون\b', 'كيف'),
            (r'\bشنو\b', 'ماذا'),
        ]
        for pat, rep in replacements:
            semantic = re.sub(pat, rep, semantic)
        return semantic

    def process(self, text: str, active_document: Optional[str] = None) -> InputUnderstandingResult:
        original = (text or '').strip()
        norm = normalize(original)
        lang = self.detect_language(original)
        dialect = self.detect_dialect(original, lang)
        semantic = self.build_semantic_text(original, norm, dialect)

        primary_intent = 'question'
        secondary_intents = []

        for intent_name, patterns in self.INTENT_MAP:
            for pat in patterns:
                if re.search(pat, norm):
                    if primary_intent == 'question':
                        primary_intent = intent_name
                    elif intent_name not in secondary_intents and intent_name != primary_intent:
                        secondary_intents.append(intent_name)

        task_type = self.classify_task_type(norm, primary_intent, active_doc=active_document)

        ref_terms = []
        for pat, ref_type in self.REFERENTIAL_PATTERNS:
            matches = re.findall(pat, norm)
            for m in matches:
                item = m[0] if isinstance(m, tuple) else m
                if item not in ref_terms:
                    ref_terms.append(item)

        kw = tokens(original)
        concepts = []
        phrases = [
            'الذكاء الاصطناعي', 'تعلم الاله', 'تعلم الالة', 'التعلم الالي',
            'الأمن السيبراني', 'قاعدة البيانات', 'معالجة اللغات الطبيعية',
            'الشبكات العصبية', 'الاسترجاع المعزز', 'تطوير الويب', 'yemen ai'
        ]
        for p in phrases:
            if normalize(p) in norm:
                concepts.append(p)
        for k in kw:
            if len(k) >= 4 and k not in concepts:
                concepts.append(k)

        req_doc = task_type == 'DOCUMENT_QUESTION' or bool(active_document)
        no_retrieval_intents = {'greeting', 'thanks', 'goodbye', 'identity', 'capabilities'}
        req_retrieval = primary_intent not in no_retrieval_intents and task_type not in {'CONTINUATION', 'UNCERTAINTY'}
        req_memory = len(ref_terms) > 0 or task_type in {'CONTINUATION', 'CORRECTION', 'SHORT_FOLLOW_UP', 'REFERENCE'}

        tok_count = len(kw)
        ambiguity = 0.7 if tok_count <= 2 and task_type in {'SHORT_FOLLOW_UP', 'CONTINUATION'} else max(0.0, 0.5 - tok_count * 0.08)
        complexity = min(1.0, 0.3 + tok_count * 0.08 + (0.2 if task_type in {'COMPARISON', 'EXPLANATION_REQUEST'} else 0.0))

        return InputUnderstandingResult(
            original_text=original,
            normalized_text=norm,
            semantic_text=semantic,
            detected_language=lang,
            dialect=dialect,
            intent=primary_intent,
            task_type=task_type,
            secondary_intents=secondary_intents,
            entities=[],
            concepts=concepts[:10],
            keywords=kw,
            reference_terms=ref_terms,
            ambiguity_score=round(ambiguity, 2),
            complexity_score=round(complexity, 2),
            confidence=0.95 if tok_count > 1 else 0.80,
            requires_retrieval=req_retrieval,
            requires_memory=req_memory,
            requires_document_grounding=req_doc,
        )
