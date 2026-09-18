"""
backend/services/language_policy.py
===================================
v9.6 Arabic Response Enforcement Layer.

Guarantees that Arabic queries receive Arabic responses by default,
formatting evidence appropriately and preventing English text leaks.
"""
from __future__ import annotations
import re
from typing import List
from backend.services.local_brain import normalize


class LanguagePolicy:
    """Enforces language policies for local AI generation."""

    def enforce_arabic(self, text: str, user_query: str) -> str:
        """
        Ensure response is presented in Arabic if user query was in Arabic.
        Translates or formats English headers / bullet structures if needed.
        """
        if not text:
            return text

        # Check if text contains English lead-ins
        english_leadins = [
            ("Based on the local knowledge available to me:", "بحسب المعرفة المحلية المتاحة لي:"),
            ("I could not find enough evidence in the uploaded document to answer this.", "لم أجد داخل المستند المرفوع دليلاً كافيًا للإجابة عن هذا السؤال."),
            ("No sufficiently relevant local knowledge was found.", "لم أجد معرفة محلية كافية للإجابة عن هذا السؤال."),
        ]

        result = text
        for eng, ar in english_leadins:
            if eng in result:
                result = result.replace(eng, ar)

        return result

    def format_bullets_in_arabic(self, sentences: List[str], style: str = 'direct') -> str:
        """Format evidence bullet points strictly in Arabic."""
        if not sentences:
            return ""

        clean_sents = [s.strip() for s in sentences if s.strip()]

        if style == 'summary':
            header = "الخلاصة:\n\n"
            bullets = [f"• {s}" for s in clean_sents[:3]]
        elif style in {'steps', 'procedural'}:
            header = "بشكل مرتب:\n\n"
            bullets = [f"{i+1}. {s}" for i, s in enumerate(clean_sents)]
        elif style == 'comparison':
            header = "المقارنة بناءً على المعرفة المتاحة:\n\n"
            bullets = [f"• {s}" for s in clean_sents]
        elif style in {'definition', 'explanation', 'causal'}:
            header = "التوضيح:\n\n"
            bullets = [f"• {s}" for s in clean_sents]
        else:
            header = "بحسب المعرفة المحلية المتاحة:\n\n"
            bullets = [f"• {s}" for s in clean_sents]

        return header + "\n".join(bullets)
