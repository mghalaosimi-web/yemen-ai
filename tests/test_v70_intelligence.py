import os
os.environ['AI_PROVIDER']='echo'
from fastapi.testclient import TestClient
from app.main import app
from backend.rag.service import RAGService

c=TestClient(app)
def login(name='admin'):
    r=c.post('/api/auth/login',json={'username':name,'password':'YemenAI2026!'})
    assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['access_token']}
def test_intelligence_health_contract():
    r=c.get('/api/intelligence/health',headers=login())
    assert r.status_code==200
    d=r.json(); assert 'provider' in d and 'knowledge' in d and d['rag']['enabled'] is True
def test_intelligence_chat_contract():
    r=c.post('/api/intelligence/chat',json={'message':'مرحبا'},headers=login('user'))
    assert r.status_code==200
    d=r.json(); assert d['answer'] and 'sources' in d and d['status'] in {'ok','degraded'}
def test_rag_threshold_returns_list():
    assert isinstance(RAGService().context('اختبار اليمن',limit=3),list)
