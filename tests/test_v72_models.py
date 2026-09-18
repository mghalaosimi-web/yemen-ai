from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
def token(user='admin'):
 r=c.post('/api/auth/login',json={'username':user,'password':'YemenAI2026!'}); assert r.status_code==200; return r.json()['access_token']
def h(): return {'Authorization':'Bearer '+token()}
def test_model_config_echo():
 r=c.put('/api/models/config',headers=h(),json={'provider':'echo','model':'','base_url':''}); assert r.status_code==200; assert r.json()['config']['provider']=='echo'
def test_model_config_reject_remote_missing_fields():
 r=c.put('/api/models/config',headers=h(),json={'provider':'openai-compatible','model':'','base_url':''}); assert r.status_code==400
def test_model_config_permission():
 t=c.post('/api/auth/login',json={'username':'user','password':'YemenAI2026!'}).json()['access_token']; r=c.get('/api/models/config',headers={'Authorization':'Bearer '+t}); assert r.status_code==403
def test_model_reload():
 r=c.post('/api/models/reload',headers=h()); assert r.status_code==200; assert 'runtime' in r.json()
