from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)

def auth(role='trainer'):
    r=c.post('/api/auth/login',json={'username':role,'password':'YemenAI2026!'})
    assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['access_token']}

def test_v61_knowledge_delete():
    h=auth()
    r=c.post('/api/knowledge',json={'title':'v61 item','content':'delete workflow','source':'test'},headers=h); assert r.status_code==200
    kid=r.json()['id']
    assert c.delete(f'/api/knowledge/{kid}',headers=h).status_code==200

def test_v61_dataset_delete():
    h=auth()
    r=c.post('/api/datasets',params={'name':'v61-delete'},headers=h); assert r.status_code==200
    did=r.json()['id']
    assert c.delete(f'/api/datasets/{did}',headers=h).status_code==200

def test_v61_clear_conversation():
    h=auth('user')
    assert c.post('/api/chat',json={'message':'v61 conversation','session_id':'default'},headers=h).status_code==200
    r=c.delete('/api/conversations/default',headers=h); assert r.status_code==200
