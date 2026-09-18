from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
def token(role='admin'):
 r=c.post('/api/auth/login',json={'username':role,'password':'YemenAI2026!'});assert r.status_code==200;return r.json()['access_token']
def test_health():assert c.get('/api/health').status_code==200
def test_login_and_bad_login():
 assert c.post('/api/auth/login',json={'username':'admin','password':'YemenAI2026!'}).status_code==200
 assert c.post('/api/auth/login',json={'username':'admin','password':'bad'}).status_code==401
def test_knowledge_and_retrieval():
 h={'Authorization':'Bearer '+token('trainer')}
 assert c.post('/api/knowledge',json={'title':'اختبار اليمن','content':'Yemen AI منصة ذكاء اصطناعي','source':'test'},headers=h).status_code==200
 r=c.post('/api/chat',json={'message':'اختبار اليمن','session_id':'t1'});assert r.status_code==200 and 'reply' in r.json()
def test_dataset_and_export():
 assert c.post('/api/datasets',params={'name':'demo'}).status_code==200
 assert c.get('/api/export/activities.csv').status_code==403
def test_upload_rejects_bad_extension():
 h={'Authorization':'Bearer '+token('trainer')}
 r=c.post('/api/datasets/upload',data={'name':'x'},files={'file':('x.exe',b'abc')},headers=h);assert r.status_code==400
