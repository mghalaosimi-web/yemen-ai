from pathlib import Path
import os
ROOT_DIR=Path(__file__).resolve().parents[2]
DATA_DIR=ROOT_DIR/'data'; UPLOAD_DIR=DATA_DIR/'uploads'; EXPORT_DIR=DATA_DIR/'exports'
DB_PATH=DATA_DIR/'yemen_ai.db'
from app.core.version import APP_VERSION
ENVIRONMENT=os.getenv('YEMEN_AI_ENV','development').lower()
MAX_UPLOAD_MB=int(os.getenv('YEMEN_AI_MAX_UPLOAD_MB','25'))
MAX_MESSAGE_CHARS=int(os.getenv('YEMEN_AI_MAX_MESSAGE_CHARS','4000'))
SECRET_KEY=os.getenv('YEMEN_AI_SECRET_KEY','development-only-change-me')
TOKEN_TTL_MINUTES=int(os.getenv('YEMEN_AI_TOKEN_TTL_MINUTES','120'))
COOKIE_SECURE=os.getenv('YEMEN_AI_COOKIE_SECURE','true' if ENVIRONMENT=='production' else 'false').lower()=='true'
ALLOWED_UPLOAD_EXTENSIONS={'.txt','.md','.json','.csv','.pdf','.docx'}
for p in (DATA_DIR,UPLOAD_DIR,EXPORT_DIR): p.mkdir(parents=True,exist_ok=True)
if ENVIRONMENT=='production' and SECRET_KEY=='development-only-change-me':
    raise RuntimeError('YEMEN_AI_SECRET_KEY must be set in production')
