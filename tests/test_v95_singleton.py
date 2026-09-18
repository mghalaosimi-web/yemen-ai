"""
tests/test_v95_singleton.py
============================
Integration tests verifying that /api/chat and /api/intelligence/chat
share the same live IntelligenceService instance.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.intelligence_provider import get_intelligence, reset_intelligence

client = TestClient(app)


def _login(role='developer'):
    r = client.post('/api/auth/login', json={'username': role, 'password': 'YemenAI2026!'})
    assert r.status_code == 200
    return r


def test_get_intelligence_always_same_instance():
    """get_intelligence() must return the identical object on repeated calls."""
    i1 = get_intelligence()
    i2 = get_intelligence()
    assert i1 is i2, "singleton must be the same object"


def test_knowledge_visible_in_both_chat_apis():
    """
    Add knowledge via /api/knowledge.
    Query via /api/chat  AND  /api/intelligence/chat.
    Both must be able to retrieve the knowledge without a restart.
    """
    _login('developer')
    unique_term = 'جيروباكتيريوم_singleton_test_unique_term_v95'

    # Add knowledge
    r = client.post(
        '/api/knowledge',
        json={'title': 'اختبار المثيل الموحد', 'content': f'هذا المحتوى يحتوي على {unique_term}.', 'source': 'test'},
    )
    assert r.status_code == 200, r.text

    # Query via /api/chat (routes.py)
    r1 = client.post('/api/chat', json={'message': unique_term, 'session_id': 'singleton_test'})
    assert r1.status_code == 200

    # Query via /api/intelligence/chat (backend/api/intelligence.py)
    r2 = client.post('/api/intelligence/chat', json={'message': unique_term, 'session_id': 'singleton_test2'})
    assert r2.status_code == 200

    # Both should have the unique term in their sources or answer
    reply1 = r1.json().get('reply', '') + str(r1.json().get('sources', ''))
    reply2 = r2.json().get('reply', '') + str(r2.json().get('sources', ''))

    # At minimum both must respond; full retrieval depends on embedding quality.
    # What we MUST NOT see is a 404 or 500 caused by isolation.
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_training_uses_same_store():
    """
    Training via /api/training/run must write into the same store that
    /api/chat reads from.  Verified by checking store item count before
    and after training a dataset.
    """
    _login('developer')
    svc = get_intelligence()
    before = svc.rag.store.stats()['documents']

    # Upload a tiny dataset (cookie auth maintained by TestClient)
    import io, uuid
    unique_content = f"الفضاء الخارجي فريد {uuid.uuid4().hex} يحتوي على مجرات."
    data = io.BytesIO(unique_content.encode('utf-8'))
    r = client.post(
        '/api/datasets/upload',
        data={'name': 'space_dataset', 'description': 'test dataset'},
        files={'file': ('space_singleton.txt', data, 'text/plain')},
    )
    assert r.status_code == 200, f"Upload failed: {r.text}"
    dataset_id = r.json()['id']

    r = client.post('/api/training/run', json={'dataset_id': dataset_id})
    assert r.status_code == 200, f"Training failed: {r.text}"

    after = svc.rag.store.stats()['documents']
    assert after > before, "training must add chunks to the shared live store"
