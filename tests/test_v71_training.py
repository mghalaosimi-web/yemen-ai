from fastapi.testclient import TestClient
from app.main import app
from app.data.database import create_dataset
from app.core.config import UPLOAD_DIR
c=TestClient(app)
def token(role='trainer'):
 r=c.post('/api/auth/login',json={'username':role,'password':'YemenAI2026!'});assert r.status_code==200;return r.json()['access_token']
def test_training_status_requires_auth(): assert c.get('/api/training/status').status_code==401
def test_training_run_text_dataset():
 fn='training_test_v71.txt';(UPLOAD_DIR/fn).write_text('اليمن بلد عربي. صنعاء مدينة تاريخية. المعرفة تساعد النظام على الإجابة.',encoding='utf-8');did=create_dataset('training-v71','test',fn);r=c.post('/api/training/run',json={'dataset_id':did},headers={'Authorization':'Bearer '+token()});assert r.status_code==200,r.text;assert r.json()['status']=='completed';assert r.json()['chunks']>=1
