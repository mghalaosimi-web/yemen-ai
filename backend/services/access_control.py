from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class KnowledgeAccessContext:
    user_id: str = "owner"
    role: str = "admin"
    owner_id: str = "owner"
    allowed_scopes: List[str] = field(default_factory=lambda: ["public", "system", "project", "private", "document", "session"])
    project_ids: List[str] = field(default_factory=list)
    document_ids: List[str] = field(default_factory=list)
    session_id: str = "default"

    def is_scope_allowed(self, scope: str) -> bool:
        if not scope:
            return True
        return scope in self.allowed_scopes


def filter_by_access_scope(hits: List[Dict[str, Any]], access_context: KnowledgeAccessContext) -> List[Dict[str, Any]]:
    filtered = []
    for hit in hits:
        meta = hit.get("metadata", {})
        item_scope = meta.get("owner_scope") or meta.get("scope") or "public"

        # Check scope permissions
        if not access_context.is_scope_allowed(item_scope):
            continue

        # Private scope requires owner match
        if item_scope == "private":
            item_owner = meta.get("owner") or meta.get("owner_id") or "owner"
            if access_context.user_id != item_owner and access_context.role != "admin":
                continue

        # Document scope check
        if item_scope == "document":
            doc_id = meta.get("document_id")
            if doc_id and access_context.document_ids and doc_id not in access_context.document_ids:
                continue

        # Session scope check
        if item_scope == "session":
            sess_id = meta.get("session_id")
            if sess_id and sess_id != access_context.session_id:
                continue

        filtered.append(hit)

    return filtered
