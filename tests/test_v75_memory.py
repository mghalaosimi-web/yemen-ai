from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
def token():
 r=c.post('/api/auth/login',json={'username':'user','password':'YemenAI2026!'}); assert r.status_code==200; return r.json()['access_token']
def test_memory_roundtrip():
 h={'Authorization':'Bearer '+token()}; sid='v75-test'
 r=c.post('/api/intelligence/chat',json={'message':'اسمي محمد وهذا اختبار لذاكرة الجلسة','session_id':sid},headers=h); assert r.status_code==200
 r=c.get('/api/intelligence/memory/'+sid,headers=h); assert r.status_code==200 and len(r.json()['history'])>=2
 r=c.post('/api/intelligence/feedback',json={'session_id':sid,'message':'اختبار','answer':'جواب','rating':5},headers=h); assert r.status_code==200
 r=c.delete('/api/intelligence/memory/'+sid,headers=h); assert r.status_code==200
