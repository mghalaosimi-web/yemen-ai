from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def login(role='admin'):
    r=client.post('/api/auth/login',json={'username':role,'password':'YemenAI2026!'});assert r.status_code==200;return r

def test_health():assert client.get('/api/health').status_code==200
def test_chat_requires_auth():assert client.post('/api/chat',json={'message':'مرحبا','session_id':'test'}).status_code==401
def test_chat_authenticated():login('user');r=client.post('/api/chat',json={'message':'مرحبا','session_id':'test'});assert r.status_code==200 and 'reply' in r.json()
def test_knowledge_requires_role():
    client.post('/api/auth/logout');assert client.post('/api/knowledge',json={'title':'اليمن','content':'بلد عربي'}).status_code==401
def test_knowledge_authenticated():login('developer');assert client.post('/api/knowledge',json={'title':'اليمن','content':'بلد عربي','source':'test'}).status_code==200
def test_dashboard_role_gate():
    client.post('/api/auth/logout');login('user');assert client.get('/api/dashboard').status_code==403
    client.post('/api/auth/logout');login('admin');assert client.get('/api/dashboard').status_code==200
def test_export_role_gate():
    client.post('/api/auth/logout');login('user');assert client.get('/api/export/activities.csv').status_code==403
    client.post('/api/auth/logout');login('admin');assert client.get('/api/export/activities.csv').status_code==200
