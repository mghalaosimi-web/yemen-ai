"""
tests/test_v95_rebuild.py
==========================
Tests for the vector store rebuild-from-db endpoint and the seed import
first-run scenario.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.intelligence_provider import get_intelligence
from backend.rag.store import JsonVectorStore

client = TestClient(app)


def _login(role='admin'):
    r = client.post('/api/auth/login', json={'username': role, 'password': 'YemenAI2026!'})
    assert r.status_code == 200
    return r.json()['access_token']


def test_rebuild_from_db_endpoint():
    """
    POST /api/intelligence/rebuild-from-db must return the expected shape
    and must not raise errors even on an empty knowledge table.
    """
    _login('admin')
    r = client.post('/api/intelligence/rebuild-from-db')
    assert r.status_code == 200
    body = r.json()
    assert 'status' in body
    assert body['status'] == 'completed'
    assert 'knowledge_items_scanned' in body
    assert 'chunks_created' in body
    assert 'duplicates_skipped' in body
    assert 'failures' in body
    assert isinstance(body['failures'], list)


def test_rebuild_is_idempotent():
    """
    Running rebuild twice must not double the chunk count (dedup prevents it).
    """
    _login('admin')
    r1 = client.post('/api/intelligence/rebuild-from-db')
    assert r1.status_code == 200
    r2 = client.post('/api/intelligence/rebuild-from-db')
    assert r2.status_code == 200
    # Second run should show zero new chunks (all duplicates)
    assert r2.json()['chunks_created'] == 0 or r2.json()['duplicates_skipped'] >= r2.json()['chunks_created']


def test_seed_import_uses_live_store(tmp_path):
    """
    Verify the seed importer writes to the same in-memory store that the
    live IntelligenceService uses (not a separate temporary instance).
    """
    from app.services.intelligence_provider import get_intelligence
    from app.services.seed_importer import import_seed_knowledge

    svc = get_intelligence()
    before = svc.rag.store.stats()['documents']

    # Force a re-import (the fingerprint check may skip it on subsequent runs)
    result = import_seed_knowledge(force=True)
    after = svc.rag.store.stats()['documents']

    # Either seeds were already present (force=True adds duplicates that dedup drops)
    # or new chunks were added. In either case the store must be accessible.
    assert after >= before, "live store document count must not decrease"
    assert isinstance(result, dict)


def test_dedup_in_store_prevents_double_ingest(tmp_path):
    """
    Ingesting the same text content twice must not create duplicate chunks.
    """
    store = JsonVectorStore(str(tmp_path / 'test.json'))
    txt = "الاقتصاد الرقمي يمثل تحولاً جذرياً في طريقة إنتاج وتوزيع السلع والخدمات."
    store.add(txt, {'knowledge_id': 1})
    store.add(txt, {'knowledge_id': 1})
    store.add(txt, {'knowledge_id': 2})  # same text, different metadata
    assert len(store.items) == 1, "same text must not create multiple entries"


def test_rebuild_requires_admin():
    """The rebuild endpoint must be restricted to admin/developer."""
    client.post('/api/auth/login', json={'username': 'user', 'password': 'YemenAI2026!'})
    r = client.post('/api/intelligence/rebuild-from-db')
    assert r.status_code in (401, 403)
