from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List

AR_DIGITS_MAP = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

PREFIXES = ['ال', 'وال', 'فال', 'بال', 'كال', 'لل', 'و', 'ف', 'ب', 'ك', 'ل']
SUFFIXES = ['ات', 'ون', 'ين', 'ان', 'هم', 'ها', 'كم', 'نا', 'ه', 'ي', 'ة']

DIALECT_MAP = {
    "ايش": "ماذا",
    "وش": "ماذا",
    "شو": "ماذا",
    "ليش": "لماذا",
    "ليه": "لماذا",
    "ابغى": "أريد",
    "أبغى": "أريد",
    "عايز": "أريد",
    "كذا": "هكذا",
    "خلاص": "تم",
    "تمام": "حسنًا",
    "حق": "خاص",
    "سويناه": "فعلناه",
    "سوينا": "فعلنا",
    "عملنا": "فعلنا",
    "ايش هو": "ما هو",
    "وش هو": "ما هو",
    "شو هو": "ما هو"
}

@dataclass
class ArabicNormalizedText:
    original_text: str
    normalized_text: str
    search_tokens: List[str]
    light_stems: List[str]
    dialect_normalized_query: str = ""
    semantic_query: str = ""


class ArabicNormalizer:
    """Advanced Arabic Linguistic Normalization & Light Stemming Engine."""

    def normalize_dialect(self, text: str) -> str:
        t = text
        for d_term, msa_term in DIALECT_MAP.items():
            pattern = r'\b' + re.escape(d_term) + r'\b'
            t = re.sub(pattern, msa_term, t)
        return t

    def normalize(self, text: str) -> ArabicNormalizedText:
        raw = str(text or '')
        # 1. Arabic & English digit normalization
        t = raw.translate(AR_DIGITS_MAP)
        t = t.lower()

        # Dialect normalization step
        dialect_norm = self.normalize_dialect(t)

        # 2. Letter normalization
        t = re.sub(r'[إأآا]', 'ا', t)
        t = t.replace('ى', 'ي')
        # Contextual ة -> ه
        t = t.replace('ة', 'ه')

        # 3. Remove diacritics (Harakat) and Tatweel (Kashida)
        t = re.sub(r'[ًٌٍَُِّْـ]', '', t)

        # 4. Remove unwanted punctuation, keep words, digits, and Arabic unicode range
        t_clean = re.sub(r'[^\w\s\u0600-\u06ff]', ' ', t)
        norm_str = re.sub(r'\s+', ' ', t_clean).strip()

        # 5. Extract search tokens (length >= 2)
        raw_tokens = [tok for tok in norm_str.split() if len(tok) >= 2]
        search_tokens = list(dict.fromkeys(raw_tokens))

        # 6. Conservative Light Stemming
        stems = []
        for tok in raw_tokens:
            stemmed = self.light_stem(tok)
            if stemmed and len(stemmed) >= 2:
                stems.append(stemmed)
            else:
                stems.append(tok)
        
        light_stems = list(dict.fromkeys(stems))

        semantic_q = dialect_norm
        if "آخر" in norm_str and ("شي" in norm_str or "شيء" in norm_str or "سوينا" in norm_str or "عملنا" in norm_str):
            semantic_q = "آخر تحديث أو عمل تم في المشروع الحالي"

        return ArabicNormalizedText(
            original_text=raw,
            normalized_text=norm_str,
            search_tokens=search_tokens,
            light_stems=light_stems,
            dialect_normalized_query=dialect_norm,
            semantic_query=semantic_q
        )

    def light_stem(self, word: str) -> str:
        """Light stemming that preserves word core meaning."""
        w = word
        if len(w) <= 3:
            return w

        # Strip prefixes
        for p in PREFIXES:
            if w.startswith(p) and len(w) - len(p) >= 3:
                w = w[len(p):]
                break

        # Strip suffixes
        for s in SUFFIXES:
            if w.endswith(s) and len(w) - len(s) >= 3:
                w = w[:-len(s)]
                break

        return w
