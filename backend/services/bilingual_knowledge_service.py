import re
import json
from typing import Dict, Any, List, Optional
from app.data.database import connect, initialize_database


class BilingualKnowledgeService:
    def __init__(self):
        initialize_database()

    def detect_language(self, text: str) -> str:
        if not text or not text.strip():
            return "en"
        
        has_ar = bool(re.search(r"[\u0600-\u06FF]", text))
        has_en = bool(re.search(r"[a-zA-Z]", text))

        if has_ar and has_en:
            return "mixed"
        elif has_ar:
            return "ar"
        return "en"

    def normalize_cross_language_query(self, query: str) -> Dict[str, Any]:
        lang = self.detect_language(query)
        canonical_concepts = []
        aliases_found = []

        # 1. Try full query first
        full_res = self.resolve_canonical_concept(query)
        if full_res:
            canonical_concepts.append(full_res)
            aliases_found.extend(self.get_concept_aliases(full_res))

        # 2. Tokenize and search individual terms
        tokens = re.findall(r"[\w\u0600-\u06FF]+", query)
        for token in tokens:
            resolved = self.resolve_canonical_concept(token)
            if resolved and resolved not in canonical_concepts:
                canonical_concepts.append(resolved)
                aliases_found.extend(self.get_concept_aliases(resolved))

        return {
            "original_query": query,
            "detected_language": lang,
            "canonical_concepts": canonical_concepts,
            "cross_language_aliases": list(set(aliases_found))
        }

    def link_terms(self, term_ar: str, term_en: str, canonical_id: Optional[str] = None) -> str:
        cid = canonical_id or f"concept_{term_en.lower().replace(' ', '_')}"
        with connect() as c:
            # Check existing concept
            row = c.execute("SELECT * FROM bilingual_concepts WHERE concept_id=?", (cid,)).fetchone()
            if row:
                labels = json.loads(row["labels_json"] or "{}")
                labels["ar"] = list(set(labels.get("ar", []) + [term_ar]))
                labels["en"] = list(set(labels.get("en", []) + [term_en]))
                c.execute(
                    "UPDATE bilingual_concepts SET labels_json=?, updated_at=CURRENT_TIMESTAMP WHERE concept_id=?",
                    (json.dumps(labels, ensure_ascii=False), cid)
                )
            else:
                labels = {"ar": [term_ar], "en": [term_en]}
                c.execute(
                    """
                    INSERT INTO bilingual_concepts (concept_id, canonical_id, labels_json, aliases_json, definitions_json, related_json)
                    VALUES (?, ?, ?, '[]', '{}', '[]')
                    """,
                    (cid, cid, json.dumps(labels, ensure_ascii=False))
                )

            # Insert aliases mapping
            c.execute("INSERT OR REPLACE INTO bilingual_aliases (alias, concept_id, language) VALUES (?, ?, 'ar')", (term_ar.strip(), cid))
            c.execute("INSERT OR REPLACE INTO bilingual_aliases (alias, concept_id, language) VALUES (?, ?, 'en')", (term_en.strip(), cid))

        return cid

    def get_concept_aliases(self, concept_id: str) -> List[str]:
        with connect() as c:
            row = c.execute("SELECT * FROM bilingual_concepts WHERE concept_id=?", (concept_id,)).fetchone()
            if not row:
                return []
            labels = json.loads(row["labels_json"] or "{}")
            aliases = json.loads(row["aliases_json"] or "[]")
            out = []
            for l_list in labels.values():
                out.extend(l_list)
            out.extend(aliases)
            return list(set(out))

    def resolve_canonical_concept(self, term: str) -> Optional[str]:
        initialize_database()
        t = term.strip()
        if not t:
            return None
        with connect() as c:
            row = c.execute("SELECT concept_id FROM bilingual_aliases WHERE LOWER(alias)=LOWER(?)", (t,)).fetchone()
            if row:
                return row["concept_id"]

            # Partial concept search
            row2 = c.execute("SELECT concept_id FROM bilingual_concepts WHERE concept_id=LOWER(?) OR canonical_id=LOWER(?)", (t, t)).fetchone()
            if row2:
                return row2["concept_id"]

            return None

    def search_cross_language(self, query: str) -> Dict[str, Any]:
        norm = self.normalize_cross_language_query(query)
        concepts_details = []
        with connect() as c:
            for cid in norm["canonical_concepts"]:
                row = c.execute("SELECT * FROM bilingual_concepts WHERE concept_id=?", (cid,)).fetchone()
                if row:
                    concepts_details.append({
                        "concept_id": row["concept_id"],
                        "labels": json.loads(row["labels_json"] or "{}"),
                        "aliases": json.loads(row["aliases_json"] or "[]")
                    })
        return {
            "query": query,
            "language": norm["detected_language"],
            "concepts": concepts_details,
            "expanded_terms": norm["cross_language_aliases"]
        }
