"""
tests/test_v95_provenance.py
=============================
Tests for knowledge delete cascade: deletes original chunks AND derived
training artifacts (QA cards, concept_index entries) via source_knowledge_id.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.intelligence_provider import get_intelligence

client = TestClient(app)


def _login(role='developer'):
    r = client.post('/api/auth/login', json={'username': role, 'password': 'YemenAI2026!'})
    assert r.status_code == 200
    return r.json()['access_token']


def test_knowledge_delete_removes_derived_artifacts():
    """
    Create knowledge, simulate enrichment by adding derived artifacts,
    delete the knowledge item, then verify ALL artifacts are gone.
    """
    _login('developer')
    # Add a knowledge item
    r = client.post(
        '/api/knowledge',
        json={
            'title': 'اختبار حذف المعرفة والمشتقات',
            'content': 'قاعدة البيانات العلائقية تستخدم الجداول لتنظيم البيانات وتسهيل الاستعلام عنها.',
            'source': 'test_provenance',
        },
    )
    assert r.status_code == 200
    kid = r.json()['id']

    store = get_intelligence().rag.store

    # Manually add derived artifacts with source_knowledge_id (mimicking training pipeline)
    store.add(
        f"سؤال: ما هي قاعدة البيانات العلائقية؟\nإجابة: تستخدم الجداول لتنظيم البيانات.",
        {'knowledge_id': kid, 'source_knowledge_id': kid, 'training_artifact': 'qa_card'},
    )
    store.add(
        "مفاهيم مرتبطة: قاعدة البيانات، جداول، استعلام",
        {'knowledge_id': kid, 'source_knowledge_id': kid, 'training_artifact': 'concept_index'},
    )

    # Count items linked to this knowledge_id before deletion
    linked_before = [
        x for x in store.items
        if x.get('metadata', {}).get('knowledge_id') == kid
        or x.get('metadata', {}).get('source_knowledge_id') == kid
    ]
    assert len(linked_before) >= 3, f"expected >= 3 linked items, got {len(linked_before)}"

    # Delete the knowledge item
    r = client.delete(f'/api/knowledge/{kid}')
    assert r.status_code == 200
    body = r.json()
    assert body['removed_primary'] + body['removed_derived'] > 0

    # Verify nothing linked to kid remains
    linked_after = [
        x for x in store.items
        if x.get('metadata', {}).get('knowledge_id') == kid
        or x.get('metadata', {}).get('source_knowledge_id') == kid
    ]
    assert linked_after == [], f"expected 0 items after delete, found {len(linked_after)}"


def test_retrieval_cannot_return_deleted_knowledge():
    """
    After deleting knowledge, a targeted query must not return that content.
    """
    _login('developer')
    unique = "ميثيل_ثلاثي_بيوتيل_إيثر_اختبار_الحذف_unique_v95"
    r = client.post(
        '/api/knowledge',
        json={'title': 'معرفة مؤقتة', 'content': f'هذه المعرفة المؤقتة تحتوي على: {unique}', 'source': 'test'},
    )
    assert r.status_code == 200
    kid = r.json()['id']

    # Delete immediately
    r = client.delete(f'/api/knowledge/{kid}')
    assert r.status_code == 200

    # Query for the unique term
    store = get_intelligence().rag.store
    results = get_intelligence().rag.context(unique, limit=5, min_score=0.0)
    texts = [h['text'] for h in results]
    assert not any(unique in t for t in texts), "deleted content must not appear in retrieval"
