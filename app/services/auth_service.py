from datetime import datetime,timedelta,timezone
import hashlib,hmac,base64,json
from fastapi import HTTPException
from app.core.config import SECRET_KEY,TOKEN_TTL_MINUTES

def hash_password(v:str)->str:
    salt=b'yemen-ai-v4'
    return hashlib.pbkdf2_hmac('sha256',v.encode(),salt,200000).hex()
def verify_password(v:str,h:str)->bool:return hmac.compare_digest(hash_password(v),h)
def _b64(b):return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
def _unb64(s):return base64.urlsafe_b64decode(s+'='*(-len(s)%4))
def create_token(username:str,role:str)->str:
    payload={'sub':username,'role':role,'exp':int((datetime.now(timezone.utc)+timedelta(minutes=TOKEN_TTL_MINUTES)).timestamp())}
    body=_b64(json.dumps(payload,separators=(',',':')).encode());sig=_b64(hmac.new(SECRET_KEY.encode(),body.encode(),hashlib.sha256).digest());return body+'.'+sig
def decode_token(value:str)->dict:
    try:
        body,sig=value.split('.',1);expected=_b64(hmac.new(SECRET_KEY.encode(),body.encode(),hashlib.sha256).digest())
        if not hmac.compare_digest(sig,expected):raise ValueError
        payload=json.loads(_unb64(body))
        if payload.get('exp',0)<int(datetime.now(timezone.utc).timestamp()):raise ValueError
        return payload
    except Exception:raise HTTPException(401,'Invalid or expired token')
