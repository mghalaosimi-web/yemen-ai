import os
import re
import json
import yaml
from typing import Dict, Any, List, Optional
from backend.services.personal_knowledge_service import PersonalKnowledgeService, PersonalFact


class PersonalContextImporter:
    def __init__(self):
        self.service = PersonalKnowledgeService()

    def import_context(self, source_path: Optional[str] = None, content: Optional[str] = None, source_id: str = "master_context") -> Dict[str, Any]:
        """Import explicit personal & project context from a file or text string.
        
        If no file or content is physically provided, return status = 'awaiting_source'.
        """
        if not source_path and not content:
            return {
                "source_id": source_id,
                "status": "awaiting_source",
                "facts_imported": 0,
                "duplicates_skipped": 0,
                "conflicts_detected": 0,
                "message": "No source file or content supplied. Awaiting source material."
            }

        text_content = ""
        file_ext = "txt"

        if source_path:
            if not os.path.exists(source_path):
                return {
                    "source_id": source_id,
                    "status": "awaiting_source",
                    "facts_imported": 0,
                    "duplicates_skipped": 0,
                    "conflicts_detected": 0,
                    "message": f"Source path '{source_path}' does not exist. Awaiting source material."
                }
            file_ext = os.path.splitext(source_path)[1].lower().lstrip(".")
            source_id = os.path.basename(source_path)
            try:
                with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
                    text_content = f.read()
            except Exception as e:
                return {
                    "source_id": source_id,
                    "status": "failed",
                    "error": str(e)
                }
        else:
            text_content = content or ""

        extracted_facts = self._extract_explicit_facts(text_content, file_ext, source_id)
        
        facts_imported = 0
        duplicates_skipped = 0
        conflicts_detected = 0

        for raw_fact in extracted_facts:
            raw_fact["source_id"] = source_id
            raw_fact["source_type"] = "personal_context"
            raw_fact["visibility"] = "private"

            # Check duplicates
            existing = self.service.search_facts(query=raw_fact["object"], domain=raw_fact.get("domain"))
            is_dup = False
            for ef in existing:
                if ef.subject == raw_fact["subject"] and ef.predicate == raw_fact["predicate"] and ef.object == raw_fact["object"]:
                    is_dup = True
                    break

            if is_dup:
                duplicates_skipped += 1
                continue

            conflicts = self.service.detect_conflicts(raw_fact)
            if conflicts:
                conflicts_detected += len(conflicts)

            self.service.add_fact(raw_fact)
            facts_imported += 1

        return {
            "source_id": source_id,
            "status": "imported",
            "facts_imported": facts_imported,
            "duplicates_skipped": duplicates_skipped,
            "conflicts_detected": conflicts_detected
        }

    def _extract_explicit_facts(self, content: str, ext: str, source_id: str) -> List[Dict[str, Any]]:
        facts = []
        if ext in ["json"]:
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    return self._facts_from_dict(data, source_id)
            except Exception:
                pass
        elif ext in ["yaml", "yml"]:
            try:
                data = yaml.safe_load(content)
                if isinstance(data, dict):
                    return self._facts_from_dict(data, source_id)
            except Exception:
                pass

        # Text/Markdown line parsing
        lines = content.splitlines()
        current_section = "general"
        current_domain = "identity"

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check section header
            if line_str.startswith("#"):
                current_section = line_str.lstrip("#").strip().lower()
                current_domain = self._map_section_to_domain(current_section)
                continue

            # Key-value pattern: Key: Value or - Key: Value
            kv_match = re.match(r"^[-*]?\s*([A-Za-z0-9_\s\u0600-\u06FF]+)[:=]\s*(.+)$", line_str)
            if kv_match:
                key = kv_match.group(1).strip()
                val = kv_match.group(2).strip()

                if val and val.lower() != "unknown":
                    lang = "ar" if re.search(r"[\u0600-\u06FF]", line_str) else "en"
                    facts.append({
                        "subject": "owner",
                        "predicate": key.lower().replace(" ", "_"),
                        "object": val,
                        "domain": current_domain,
                        "language": lang,
                        "confidence": 1.0,
                        "source_section": current_section
                    })

        return facts

    def _facts_from_dict(self, data: Dict[str, Any], source_id: str) -> List[Dict[str, Any]]:
        facts = []
        for k, v in data.items():
            domain = self._map_section_to_domain(k)
            if isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    facts.append({
                        "subject": "owner",
                        "predicate": f"{k}_{sub_k}".lower(),
                        "object": str(sub_v),
                        "domain": domain,
                        "language": "ar" if re.search(r"[\u0600-\u06FF]", str(sub_v)) else "en",
                        "confidence": 1.0,
                        "source_section": k
                    })
            elif isinstance(v, list):
                for item in v:
                    facts.append({
                        "subject": "owner",
                        "predicate": k.lower(),
                        "object": str(item),
                        "domain": domain,
                        "language": "ar" if re.search(r"[\u0600-\u06FF]", str(item)) else "en",
                        "confidence": 1.0,
                        "source_section": k
                    })
            else:
                facts.append({
                    "subject": "owner",
                    "predicate": k.lower(),
                    "object": str(v),
                    "domain": domain,
                    "language": "ar" if re.search(r"[\u0600-\u06FF]", str(v)) else "en",
                    "confidence": 1.0,
                    "source_section": k
                })
        return facts

    def _map_section_to_domain(self, section: str) -> str:
        sec = section.lower()
        if "project" in sec:
            return "projects"
        if "skill" in sec or "tech" in sec:
            return "skills"
        if "interest" in sec:
            return "technical_interests"
        if "style" in sec or "pref" in sec:
            return "working_style"
        if "goal" in sec:
            return "goals"
        return "identity"
