from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
def test_feedback_endpoint():
    r=c.post('/api/auth/login',json={'username':'user','password':'YemenAI2026!'})
    h={'Authorization':'Bearer '+r.json()['access_token']}
    x=c.post('/api/chat/feedback',json={'message':'سؤال','answer':'جواب','rating':2,'notes':'التصحيح الصحيح هو أن الإجابة تحتاج إلى توضيح أدق.'},headers=h)
    assert x.status_code==200 and x.json()['saved'] is True and x.json()['learned_correction'] is True
