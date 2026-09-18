from fastapi.testclient import TestClient
from app.main import app

def test_pages_load():
    c=TestClient(app)
    assert c.get('/').status_code==200
    assert c.get('/static/style.css').status_code==200

def test_demo_login():
    c=TestClient(app)
    r=c.post('/api/auth/login',json={'username':'admin','password':'YemenAI2026!'})
    assert r.status_code==200
