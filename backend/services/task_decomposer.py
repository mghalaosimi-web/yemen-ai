from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any
from backend.services.arabic_normalizer import ArabicNormalizer

@dataclass
class DecomposedTask:
    task_type: str  # 'simple_question', 'comparison', 'multi_step', 'analysis', 'research', 'document_question'
    complexity: float  # 0.0 to 1.0
    subtask_count: int
    subtasks: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_type': self.task_type,
            'complexity': round(self.complexity, 2),
            'subtask_count': self.subtask_count,
            'subtasks': self.subtasks,
            'confidence': round(self.confidence, 2)
        }


class TaskDecomposer:
    """Deep Reasoning Task Decomposer."""

    def __init__(self):
        self.normalizer = ArabicNormalizer()

    def decompose(self, query: str, is_document_active: bool = False) -> DecomposedTask:
        norm = self.normalizer.normalize(query).normalized_text
        words = norm.split()
        word_count = len(words)

        # 1. Document-Grounded Query
        if is_document_active or any(k in norm for k in ['المستند', 'الملف', 'التقرير', 'في المستند']):
            return DecomposedTask(
                task_type='document_question',
                complexity=0.5,
                subtask_count=2,
                subtasks=['تحديد المقاطع ذات الصلة بالمستند', 'التحقق من الدليل واستخلاص الإجابة'],
                confidence=0.95
            )

        # 2. Comparison Query ("قارن بين X و Y")
        if any(k in norm for k in ['قارن', 'مقارنه', 'مقارنة', 'الفرق بين', 'ايش الفرق', 'وش الفرق', 'compare', 'vs']):
            # Extract entities X and Y
            m = re.search(r'(?:قارن بين|الفرق بين|مقارنة بين|مقارنه بين)\s+([\w\s]+?)\s+(?:و|مع|مقابل)\s+([\w\s]+)', norm)
            ent1 = m.group(1).strip() if m else 'العنصر الأول'
            ent2 = m.group(2).strip() if m else 'العنصر الثاني'
            
            subtasks = [
                f'تعريف وتحليل {ent1}',
                f'تعريف وتحليل {ent2}',
                f'مقارنة الخصائص والفروق بين {ent1} و {ent2}',
                'تقديم التقييم والتوصية النهائية'
            ]
            return DecomposedTask(
                task_type='comparison',
                complexity=0.85,
                subtask_count=len(subtasks),
                subtasks=subtasks,
                confidence=0.90
            )

        # 3. Procedural / Multi-step Query ("كيف ابدا", "خطوات", "طريقة")
        if any(k in norm for k in ['خطوات', 'طريقة', 'كيف ابدا', 'كيف ابدأ', 'كيف يتم', 'كيف اسوي', 'steps', 'how to']):
            subtasks = [
                'تحديد المتطلبات الأساسية والهدف',
                'تسلسل الخطوات التنفيذية بالترتيب',
                'تحديد الشروط أو نقاط التحقق من النجاح'
            ]
            return DecomposedTask(
                task_type='multi_step',
                complexity=0.75,
                subtask_count=len(subtasks),
                subtasks=subtasks,
                confidence=0.88
            )

        # 4. Research / Analysis Query ("حلل", "مستقبل", "دراسة", "تقييم")
        if any(k in norm for k in ['حلل', 'تحليل', 'دراسه', 'دراسة', 'مستقبل', 'آفاق', 'تقييم', 'analyze', 'evaluate']):
            subtasks = [
                'مراجعة وتجمع البيانات والأدلة المحلية',
                'تحليل الأبعاد والعوامل الرئيسية',
                'استنتاج النظرة المستقبلية والتوصيات'
            ]
            return DecomposedTask(
                task_type='research',
                complexity=0.90,
                subtask_count=len(subtasks),
                subtasks=subtasks,
                confidence=0.85
            )

        # 5. Simple Direct Question
        if word_count <= 6:
            return DecomposedTask(
                task_type='simple_question',
                complexity=0.3,
                subtask_count=1,
                subtasks=['الإجابة المباشرة المعتمدة على المعرفة'],
                confidence=0.95
            )

        # General Reasoning Question fallback
        return DecomposedTask(
            task_type='reasoning_question',
            complexity=0.6,
            subtask_count=2,
            subtasks=['استرجاع المعرفة المحلية المفاهيمية', 'صياغة الإجابة الموضحة'],
            confidence=0.85
        )
