from fastapi.testclient import TestClient
from main import app
from backend.services.knowledge_graph import KnowledgeGraphService

def test_graph_extract_and_overview():
    g=KnowledgeGraphService(); r=g.ingest_text('Yemen AI منصة ذكاء اصطناعي ومعرفة وهندسة برمجيات', 'test')
    assert r['nodes'] >= 2
    assert g.overview()['stats']['nodes'] >= 2

def test_graph_api_requires_auth_then_works():
    c=TestClient(app)
    assert c.get('/api/graph/overview').status_code in (401,403)
    login=c.post('/api/auth/login',json={'username':'admin','password':'YemenAI2026!'})
    assert login.status_code==200
    assert c.get('/api/graph/overview').status_code==200
