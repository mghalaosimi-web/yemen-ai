import uuid
import json
import time
from typing import Dict, Any, List, Optional
from app.data.database import connect, initialize_database


class PersonalFact:
    def __init__(
        self,
        fact_id: str,
        subject: str,
        predicate: str,
        object_val: str,
        domain: str,
        language: str = "en",
        confidence: float = 1.0,
        source_id: str = "",
        source_type: str = "personal_context",
        source_section: str = "",
        visibility: str = "private",
        status: str = "active",
        created_at: str = "",
        updated_at: str = "",
        superseded_by: str = "",
        version: int = 1
    ):
        self.fact_id = fact_id
        self.subject = subject
        self.predicate = predicate
        self.object = object_val
        self.domain = domain
        self.language = language
        self.confidence = float(confidence)
        self.source_id = source_id
        self.source_type = source_type
        self.source_section = source_section
        self.visibility = visibility
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.superseded_by = superseded_by
        self.version = version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "domain": self.domain,
            "language": self.language,
            "confidence": self.confidence,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "source_section": self.source_section,
            "visibility": self.visibility,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "superseded_by": self.superseded_by,
            "version": self.version
        }

    @classmethod
    def from_row(cls, row) -> "PersonalFact":
        d = dict(row)
        return cls(
            fact_id=d["fact_id"],
            subject=d["subject"],
            predicate=d["predicate"],
            object_val=d["object"],
            domain=d["domain"],
            language=d.get("language", "en"),
            confidence=d.get("confidence", 1.0),
            source_id=d.get("source_id", ""),
            source_type=d.get("source_type", "personal_context"),
            source_section=d.get("source_section", ""),
            visibility=d.get("visibility", "private"),
            status=d.get("status", "active"),
            created_at=str(d.get("created_at", "")),
            updated_at=str(d.get("updated_at", "")),
            superseded_by=d.get("superseded_by", ""),
            version=d.get("version", 1)
        )


class PersonalKnowledgeService:
    VALID_DOMAINS = {
        "identity",
        "professional_profile",
        "skills",
        "technical_interests",
        "projects",
        "goals",
        "working_style",
        "preferred_languages",
        "communication_style",
        "technology_preferences",
        "development_preferences",
        "learning_preferences",
        "long_term_projects"
    }

    def __init__(self):
        initialize_database()

    def add_fact(self, fact_data: Dict[str, Any]) -> PersonalFact:
        subject = fact_data.get("subject", "owner")
        predicate = fact_data.get("predicate", "unknown")
        object_val = str(fact_data.get("object", "unknown"))
        domain = fact_data.get("domain", "identity")
        if domain not in self.VALID_DOMAINS:
            domain = "identity"

        language = fact_data.get("language", "en")
        confidence = float(fact_data.get("confidence", 1.0))
        source_id = fact_data.get("source_id", "explicit_input")
        source_type = fact_data.get("source_type", "personal_context")
        source_section = fact_data.get("source_section", "")
        visibility = fact_data.get("visibility", "private")

        fact_id = fact_data.get("fact_id") or f"pf_{uuid.uuid4().hex[:12]}"

        # Check existing matching fact (same subject + predicate) for conflict / deduplication
        existing_conflicts = self.detect_conflicts({"subject": subject, "predicate": predicate, "object": object_val})
        
        with connect() as c:
            c.execute(
                """
                INSERT INTO personal_facts (
                    fact_id, subject, predicate, object, domain, language, confidence,
                    source_id, source_type, source_section, visibility, status, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 1)
                """,
                (
                    fact_id, subject, predicate, object_val, domain, language, confidence,
                    source_id, source_type, source_section, visibility
                )
            )
            # Record initial version
            version_id = f"pfv_{uuid.uuid4().hex[:12]}"
            c.execute(
                """
                INSERT INTO personal_fact_versions (version_id, fact_id, value, status, source_id)
                VALUES (?, ?, ?, 'active', ?)
                """,
                (version_id, fact_id, object_val, source_id)
            )

        # Auto-supersede old facts if exact same subject and predicate exist
        for conflict in existing_conflicts:
            old_id = conflict.get("fact_id")
            if old_id and old_id != fact_id:
                self.supersede_fact(old_id, fact_id)

        return self.get_fact(fact_id)

    def get_fact(self, fact_id: str) -> Optional[PersonalFact]:
        with connect() as c:
            row = c.execute("SELECT * FROM personal_facts WHERE fact_id=?", (fact_id,)).fetchone()
            return PersonalFact.from_row(row) if row else None

    def search_personal_context(self, query: str, user_id: str = "owner", limit: int = 5) -> List[Dict[str, Any]]:
        facts = self.search_facts(query, visibility="private")
        return [
            {
                "category": f.domain,
                "content": f"{f.predicate}: {f.object}",
                "confidence": f.confidence,
                "subject": f.subject,
                "user_id": user_id
            }
            for f in facts[:limit]
            if f.subject == user_id or f.subject == "owner" or user_id == "admin" or user_id == "owner"
        ]

    def upsert_personal_context(self, user_id: str, category: str, content: str) -> PersonalFact:
        domain = category if category in self.VALID_DOMAINS else "identity"
        return self.add_fact({
            "subject": user_id,
            "predicate": category,
            "object": content,
            "domain": domain,
            "visibility": "private"
        })

    def search_facts(self, query: str, domain: Optional[str] = None, visibility: str = "private") -> List[PersonalFact]:
        q = f"%{query.strip()}%"
        sql = "SELECT * FROM personal_facts WHERE status='active' AND (subject LIKE ? OR predicate LIKE ? OR object LIKE ?)"
        params = [q, q, q]

        if domain:
            sql += " AND domain=?"
            params.append(domain)
        if visibility:
            sql += " AND visibility=?"
            params.append(visibility)

        sql += " ORDER BY id DESC"
        with connect() as c:
            rows = c.execute(sql, params).fetchall()
            return [PersonalFact.from_row(r) for r in rows]

    def get_domain(self, domain: str) -> List[PersonalFact]:
        with connect() as c:
            rows = c.execute("SELECT * FROM personal_facts WHERE domain=? AND status='active' ORDER BY id DESC", (domain,)).fetchall()
            return [PersonalFact.from_row(r) for r in rows]

    def detect_conflicts(self, fact_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        subject = fact_data.get("subject", "owner")
        predicate = fact_data.get("predicate", "")
        object_val = str(fact_data.get("object", ""))

        if not predicate:
            return []

        with connect() as c:
            rows = c.execute(
                "SELECT * FROM personal_facts WHERE subject=? AND predicate=? AND status='active'",
                (subject, predicate)
            ).fetchall()
            conflicts = []
            for r in rows:
                d = dict(r)
                if d["object"] != object_val:
                    conflicts.append(d)
            return conflicts

    def supersede_fact(self, old_fact_id: str, new_fact_id: str) -> bool:
        with connect() as c:
            c.execute(
                "UPDATE personal_facts SET status='superseded', superseded_by=?, updated_at=CURRENT_TIMESTAMP WHERE fact_id=?",
                (new_fact_id, old_fact_id)
            )
            # update version entry
            c.execute(
                "UPDATE personal_fact_versions SET status='superseded', superseded_at=CURRENT_TIMESTAMP WHERE fact_id=?",
                (old_fact_id,)
            )
            return True

    def deactivate_fact(self, fact_id: str) -> bool:
        with connect() as c:
            cur = c.execute(
                "UPDATE personal_facts SET status='deactivated', updated_at=CURRENT_TIMESTAMP WHERE fact_id=?",
                (fact_id,)
            )
            return cur.rowcount > 0

    def update_fact(self, fact_id: str, new_object: Any, source_id: str = "") -> Optional[PersonalFact]:
        existing = self.get_fact(fact_id)
        if not existing:
            return None

        new_version = existing.version + 1
        val_str = str(new_object)

        with connect() as c:
            c.execute(
                """
                UPDATE personal_facts
                SET object=?, version=?, updated_at=CURRENT_TIMESTAMP, source_id=CASE WHEN ? != '' THEN ? ELSE source_id END
                WHERE fact_id=?
                """,
                (val_str, new_version, source_id, source_id, fact_id)
            )
            version_id = f"pfv_{uuid.uuid4().hex[:12]}"
            c.execute(
                """
                INSERT INTO personal_fact_versions (version_id, fact_id, value, status, source_id)
                VALUES (?, ?, ?, 'active', ?)
                """,
                (version_id, fact_id, val_str, source_id or existing.source_id)
            )

        return self.get_fact(fact_id)

    def get_profile_summary(self) -> Dict[str, Any]:
        with connect() as c:
            rows = c.execute("SELECT * FROM personal_facts WHERE status='active' AND visibility='private'").fetchall()
            facts = [PersonalFact.from_row(r).to_dict() for r in rows]

        domain_counts = {}
        for f in facts:
            d = f["domain"]
            domain_counts[d] = domain_counts.get(d, 0) + 1

        return {
            "total_facts": len(facts),
            "domains": domain_counts,
            "facts": facts
        }
