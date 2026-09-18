import pytest
from backend.services.access_control import KnowledgeAccessContext, filter_by_access_scope


def test_access_scope_filtering():
    ctx_owner = KnowledgeAccessContext(user_id="owner", role="admin", allowed_scopes=["public", "private"])
    ctx_guest = KnowledgeAccessContext(user_id="guest", role="user", allowed_scopes=["public"])

    hits = [
        {"text": "Public fact", "metadata": {"owner_scope": "public"}},
        {"text": "Private fact", "metadata": {"owner_scope": "private", "owner": "owner"}},
    ]

    filtered_owner = filter_by_access_scope(hits, ctx_owner)
    filtered_guest = filter_by_access_scope(hits, ctx_guest)

    assert len(filtered_owner) == 2
    assert len(filtered_guest) == 1
    assert filtered_guest[0]["text"] == "Public fact"
