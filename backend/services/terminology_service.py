import os
import json
import yaml
from typing import Dict, Any, List, Optional
from backend.services.concept_mapper import ConceptMapper


class TerminologyService:
    def __init__(self, seed_dir: Optional[str] = None):
        self.seed_dir = seed_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge_seed", "bilingual_technical_terms")
        self.mapper = ConceptMapper()
        self.terms_registry: Dict[str, Dict[str, Any]] = {}
        self.load_registry()

    def load_registry(self):
        if not os.path.exists(self.seed_dir):
            os.makedirs(self.seed_dir, exist_ok=True)
            return

        for fname in os.listdir(self.seed_dir):
            fpath = os.path.join(self.seed_dir, fname)
            if os.path.isfile(fpath):
                ext = os.path.splitext(fname)[1].lower()
                data = None
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        if ext == ".json":
                            data = json.load(f)
                        elif ext in [".yaml", ".yml"]:
                            data = yaml.safe_load(f)
                except Exception:
                    continue

                if isinstance(data, list):
                    for item in data:
                        self.register_term(item)
                elif isinstance(data, dict):
                    if "terms" in data and isinstance(data["terms"], list):
                        for item in data["terms"]:
                            self.register_term(item)
                    else:
                        self.register_term(data)

    def register_term(self, term_data: Dict[str, Any]):
        term_en = term_data.get("english") or term_data.get("term") or ""
        term_ar = term_data.get("arabic") or ""
        concept_id = term_data.get("canonical_concept") or term_data.get("concept_id") or f"concept_{term_en.lower().replace(' ', '_')}"
        domain = term_data.get("domain", "general")
        abbreviation = term_data.get("abbreviation") or term_data.get("alias") or ""
        definition = term_data.get("definition", "")

        if not term_en and not term_ar:
            return

        entry = {
            "concept_id": concept_id,
            "term_en": term_en,
            "term_ar": term_ar,
            "abbreviation": abbreviation,
            "domain": domain,
            "definition": definition,
            "aliases": term_data.get("aliases", [])
        }

        self.terms_registry[concept_id] = entry

        # Register into concept mapper
        labels = {"ar": [term_ar] if term_ar else [], "en": [term_en] if term_en else []}
        aliases = list(set([abbreviation] + term_data.get("aliases", [])))
        aliases = [a for a in aliases if a]

        self.mapper.register_concept(
            concept_id=concept_id,
            labels=labels,
            aliases=aliases,
            definitions={"ar": definition, "en": definition} if definition else {}
        )

    def lookup(self, term: str) -> Optional[Dict[str, Any]]:
        if not term or not term.strip():
            return None
        
        t = term.strip().lower()

        # Exact concept match
        if t in self.terms_registry:
            return self.terms_registry[t]

        # Search registry entries
        for cid, data in self.terms_registry.items():
            if data["term_en"].lower() == t or data["term_ar"] == term.strip() or data["abbreviation"].lower() == t:
                return data
            for a in data.get("aliases", []):
                if a.lower() == t:
                    return data

        # Check ConceptMapper fallback
        c_resolved = self.mapper.resolve_concept(term)
        if c_resolved:
            cid = c_resolved["concept_id"]
            if cid in self.terms_registry:
                return self.terms_registry[cid]
            labels = c_resolved.get("labels", {})
            return {
                "concept_id": cid,
                "term_en": labels.get("en", [""])[0] if labels.get("en") else "",
                "term_ar": labels.get("ar", [""])[0] if labels.get("ar") else "",
                "abbreviation": c_resolved.get("aliases", [""])[0] if c_resolved.get("aliases") else "",
                "domain": "general",
                "definition": c_resolved.get("definitions", {}).get("en", ""),
                "aliases": c_resolved.get("aliases", [])
            }

        return None

    def resolve_alias(self, alias: str) -> Optional[str]:
        item = self.lookup(alias)
        return item["concept_id"] if item else None

    def search_terms(self, query: str, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        q = query.strip().lower()
        out = []
        for cid, data in self.terms_registry.items():
            if domain and data.get("domain") != domain:
                continue
            if q in data["term_en"].lower() or q in data["term_ar"] or q in data["abbreviation"].lower() or q in cid:
                out.append(data)
        return out

    def get_translations(self, term: str) -> Dict[str, str]:
        item = self.lookup(term)
        if not item:
            return {"ar": "", "en": ""}
        return {
            "ar": item.get("term_ar", ""),
            "en": item.get("term_en", "")
        }

    def get_domain_terms(self, domain: str) -> List[Dict[str, Any]]:
        return [data for data in self.terms_registry.values() if data.get("domain") == domain]
