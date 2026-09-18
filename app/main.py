from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.data.database import initialize_database, ensure_demo_users
from app.services.auth_service import hash_password, decode_token
from app.api.routes import router
from backend.api.intelligence import router as intelligence_router
from backend.api.training import router as training_router
from backend.api.models import router as models_router
from backend.api.graph import router as graph_router
from app.core.config import APP_VERSION, ENVIRONMENT

BASE = Path(__file__).resolve().parent
STATIC = BASE / 'static'

# ── Database & users ──────────────────────────────────────────────────────────
initialize_database()
ensure_demo_users(hash_password('YemenAI2026!'), repair_existing=(ENVIRONMENT == 'development'))

# ── Canonical IntelligenceService singleton ───────────────────────────────────
# Import the singleton here so it is created exactly once during startup.
# All routes will retrieve it via get_intelligence().
from app.services.intelligence_provider import get_intelligence  # noqa: E402
_intelligence = get_intelligence()  # warm up the singleton

# ── Seed knowledge ────────────────────────────────────────────────────────────
# Runs after the singleton exists so imported chunks are immediately live.
from app.services.seed_importer import import_seed_knowledge  # noqa: E402
import_seed_knowledge()

# ── FastAPI application ───────────────────────────────────────────────────────
app = FastAPI(title='Yemen AI', version=APP_VERSION, description='Yemen AI intelligent platform')
app.include_router(router)
app.include_router(intelligence_router)
app.include_router(training_router)
app.include_router(models_router)
app.include_router(graph_router)
app.mount('/static', StaticFiles(directory=STATIC), name='static')

PORTALS = {
    '/training': {'admin', 'developer', 'trainer'},
    '/developer': {'admin', 'developer'},
    '/user': {'admin', 'developer', 'trainer', 'user'},
    '/dashboard': {'admin', 'developer'},
}


@app.middleware('http')
async def portal_gate(request: Request, call_next):
    path = request.url.path
    if path in PORTALS:
        token = request.cookies.get('yemen_ai_token')
        if not token:
            return RedirectResponse('/?next=' + path, status_code=303)
        try:
            claims = decode_token(token)
        except Exception:
            return RedirectResponse('/?next=' + path, status_code=303)
        if claims.get('role') not in PORTALS[path]:
            return RedirectResponse('/?denied=1', status_code=303)
    return await call_next(request)


@app.get('/favicon.ico')
def favicon():
    return FileResponse(STATIC / 'favicon.svg', media_type='image/svg+xml')


@app.get('/')
def home():
    return FileResponse(STATIC / 'index.html')


@app.get('/training')
def training():
    return FileResponse(STATIC / 'training.html')


@app.get('/developer')
def developer():
    return FileResponse(STATIC / 'developer.html')


@app.get('/user')
def user():
    return FileResponse(STATIC / 'user.html')


@app.get('/dashboard')
def dashboard_page():
    return FileResponse(STATIC / 'dashboard.html')
