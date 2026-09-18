import json
from typing import Dict, Any, List, Optional
from app.data.database import connect, initialize_database


class ConceptMapper:
    def __init__(self):
        initialize_database()

    def register_concept(
        self,
        concept_id: str,
        labels: Optional[Dict[str, List[str]]] = None,
        aliases: Optional[List[str]] = None,
        definitions: Optional[Dict[str, str]] = None,
        related_concepts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        labels = labels or {"ar": [], "en": []}
        aliases = aliases or []
        definitions = definitions or {}
        related_concepts = related_concepts or []

        with connect() as c:
            c.execute(
                """
                INSERT INTO bilingual_concepts (concept_id, canonical_id, labels_json, aliases_json, definitions_json, related_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(concept_id) DO UPDATE SET
                    labels_json=excluded.labels_json,
                    aliases_json=excluded.aliases_json,
                    definitions_json=excluded.definitions_json,
                    related_json=excluded.related_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    concept_id,
                    concept_id,
                    json.dumps(labels, ensure_ascii=False),
                    json.dumps(aliases, ensure_ascii=False),
                    json.dumps(definitions, ensure_ascii=False),
                    json.dumps(related_concepts, ensure_ascii=False)
                )
            )

            # Insert aliases
            for lang, lbl_list in labels.items():
                for lbl in lbl_list:
                    if lbl.strip():
                        c.execute("INSERT OR REPLACE INTO bilingual_aliases (alias, concept_id, language) VALUES (?, ?, ?)", (lbl.strip(), concept_id, lang))

            for alias in aliases:
                if alias.strip():
                    c.execute("INSERT OR REPLACE INTO bilingual_aliases (alias, concept_id, language) VALUES (?, ?, 'en')", (alias.strip(), concept_id))

        return self.resolve_concept(concept_id) or {}

    def resolve_concept(self, concept_id: str) -> Optional[Dict[str, Any]]:
        initialize_database()
        with connect() as c:
            row = c.execute("SELECT * FROM bilingual_concepts WHERE concept_id=?", (concept_id,)).fetchone()
            if not row:
                # Try alias lookup
                r_alias = c.execute("SELECT concept_id FROM bilingual_aliases WHERE alias=? OR LOWER(alias)=LOWER(?)", (concept_id.strip(), concept_id.strip())).fetchone()
                if r_alias:
                    row = c.execute("SELECT * FROM bilingual_concepts WHERE concept_id=?", (r_alias["concept_id"],)).fetchone()

            if not row:
                return None

            return {
                "concept_id": row["concept_id"],
                "canonical_id": row["canonical_id"],
                "labels": json.loads(row["labels_json"] or "{}"),
                "aliases": json.loads(row["aliases_json"] or "[]"),
                "definitions": json.loads(row["definitions_json"] or "{}"),
                "related_concepts": json.loads(row["related_json"] or "[]")
            }

    def add_alias(self, concept_id: str, alias: str, language: str = "en") -> bool:
        concept = self.resolve_concept(concept_id)
        if not concept:
            return False

        aliases = concept["aliases"]
        if alias not in aliases:
            aliases.append(alias)

        with connect() as c:
            c.execute(
                "UPDATE bilingual_concepts SET aliases_json=?, updated_at=CURRENT_TIMESTAMP WHERE concept_id=?",
                (json.dumps(aliases, ensure_ascii=False), concept["concept_id"])
            )
            c.execute(
                "INSERT OR REPLACE INTO bilingual_aliases (alias, concept_id, language) VALUES (?, ?, ?)",
                (alias.strip(), concept["concept_id"], language)
            )
        return True

    def link_translation(self, concept_id: str, language: str, translation: str) -> bool:
        concept = self.resolve_concept(concept_id)
        if not concept:
            return False

        labels = concept["labels"]
        lang_list = labels.get(language, [])
        if translation not in lang_list:
            lang_list.append(translation)
        labels[language] = lang_list

        with connect() as c:
            c.execute(
                "UPDATE bilingual_concepts SET labels_json=?, updated_at=CURRENT_TIMESTAMP WHERE concept_id=?",
                (json.dumps(labels, ensure_ascii=False), concept["concept_id"])
            )
            c.execute(
                "INSERT OR REPLACE INTO bilingual_aliases (alias, concept_id, language) VALUES (?, ?, ?)",
                (translation.strip(), concept["concept_id"], language)
            )
        return True

    def get_related_concepts(self, concept_id: str) -> List[Dict[str, Any]]:
        concept = self.resolve_concept(concept_id)
        if not concept:
            return []
        related_ids = concept.get("related_concepts", [])
        out = []
        for rid in related_ids:
            rc = self.resolve_concept(rid)
            if rc:
                out.append(rc)
        return out

    def merge_concepts(self, target_concept_id: str, source_concept_id: str) -> bool:
        target = self.resolve_concept(target_concept_id)
        source = self.resolve_concept(source_concept_id)

        if not target or not source:
            return False

        # Merge labels
        merged_labels = target["labels"]
        for lang, l_list in source["labels"].items():
            merged_labels[lang] = list(set(merged_labels.get(lang, []) + l_list))

        # Merge aliases
        merged_aliases = list(set(target["aliases"] + source["aliases"]))

        # Merge definitions
        merged_defs = {**source["definitions"], **target["definitions"]}

        # Merge related
        merged_related = list(set(target["related_concepts"] + source["related_concepts"]))
        if source_concept_id in merged_related:
            merged_related.remove(source_concept_id)

        with connect() as c:
            c.execute(
                """
                UPDATE bilingual_concepts
                SET labels_json=?, aliases_json=?, definitions_json=?, related_json=?, updated_at=CURRENT_TIMESTAMP
                WHERE concept_id=?
                """,
                (
                    json.dumps(merged_labels, ensure_ascii=False),
                    json.dumps(merged_aliases, ensure_ascii=False),
                    json.dumps(merged_defs, ensure_ascii=False),
                    json.dumps(merged_related, ensure_ascii=False),
                    target["concept_id"]
                )
            )
            # Re-point aliases in bilingual_aliases table
            c.execute("UPDATE bilingual_aliases SET concept_id=? WHERE concept_id=?", (target["concept_id"], source["concept_id"]))
            # Delete old concept
            c.execute("DELETE FROM bilingual_concepts WHERE concept_id=?", (source["concept_id"],))

        return True

    def detect_duplicate_concepts(self) -> List[Dict[str, Any]]:
        duplicates = []
        with connect() as c:
            rows = c.execute("SELECT * FROM bilingual_concepts").fetchall()
            concepts = [{
                "concept_id": r["concept_id"],
                "labels": json.loads(r["labels_json"] or "{}"),
                "aliases": json.loads(r["aliases_json"] or "[]")
            } for r in rows]

        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                c1 = concepts[i]
                c2 = concepts[j]
                # Check overlapping labels/aliases
                set1 = set(c1["aliases"] + c1["labels"].get("ar", []) + c1["labels"].get("en", []))
                set2 = set(c2["aliases"] + c2["labels"].get("ar", []) + c2["labels"].get("en", []))
                intersection = set1.intersection(set2)
                if intersection:
                    duplicates.append({
                        "concept_a": c1["concept_id"],
                        "concept_b": c2["concept_id"],
                        "shared_terms": list(intersection)
                    })

        return duplicates
