from fastapi.testclient import TestClient
from app.main import app

c=TestClient(app)

def token():
    r=c.post('/api/auth/login',json={'username':'admin','password':'YemenAI2026!'})
    assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['access_token']}

def test_user_management_and_settings():
    h=token()
    name='v62_test_user'
    c.delete('/api/users/999999',headers=h)
    r=c.post('/api/users',headers=h,json={'username':name,'password':'SecurePass123','role':'user'})
    assert r.status_code in (200,409)
    users=c.get('/api/users',headers=h).json()
    u=next(x for x in users if x['username']==name)
    assert c.patch(f"/api/users/{u['id']}/role",headers=h,json={'role':'trainer'}).status_code==200
    assert c.put('/api/settings/maintenance_mode',headers=h,json={'value':False}).status_code==200
    assert c.get('/api/settings',headers=h).status_code==200
    assert c.delete(f"/api/users/{u['id']}",headers=h).status_code==200

def test_admin_guards():
    r=c.post('/api/auth/login',json={'username':'developer','password':'YemenAI2026!'})
    h={'Authorization':'Bearer '+r.json()['access_token']}
    assert c.get('/api/users',headers=h).status_code==403
