from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
def test_direct_portal_redirects_without_login():
    r=c.get('/training',follow_redirects=False); assert r.status_code in (302,303,307)
def test_login_sets_cookie_and_allows_user_portal():
    r=c.post('/api/auth/login',json={'username':'user','password':'YemenAI2026!'}); assert r.status_code==200
    r=c.get('/user'); assert r.status_code==200
def test_user_denied_developer_portal():
    c.post('/api/auth/login',json={'username':'user','password':'YemenAI2026!'})
    r=c.get('/developer',follow_redirects=False); assert r.status_code in (302,303,307)
def test_logout_removes_access():
    c.post('/api/auth/login',json={'username':'trainer','password':'YemenAI2026!'})
    c.post('/api/auth/logout'); r=c.get('/training',follow_redirects=False); assert r.status_code in (302,303,307)
