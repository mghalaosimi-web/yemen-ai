"""
app/services/seed_importer.py
==============================
Imports the bundled seed knowledge once on first startup.

Key invariants:
  • Uses the canonical IntelligenceService singleton so imported chunks
    are immediately searchable without a restart.
  • Fingerprinting prevents re-import when seeds are unchanged.
  • If vector_store.json is empty but the fingerprint says seeds were
    previously imported, the import is run again automatically (recovery).
"""
from pathlib import Path
import hashlib
from app.data.database import add_activity, get_setting, set_setting

BASE = Path(__file__).resolve().parents[2]
SEED_DIR = BASE / 'knowledge_seed'
STATE_KEY = 'seed_knowledge_import_v1'
SUPPORTED = {'.md', '.txt', '.json', '.csv'}


def _fingerprint():
    h = hashlib.sha256()
    for p in sorted(SEED_DIR.rglob('*')):
        if p.is_file() and p.suffix.lower() in SUPPORTED:
            h.update(str(p.relative_to(SEED_DIR)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def seed_status():
    files = [p for p in SEED_DIR.rglob('*') if p.is_file() and p.suffix.lower() in SUPPORTED]
    state = get_setting(STATE_KEY, {}) or {}
    return {
        'seed_directory': str(SEED_DIR),
        'files_available': len(files),
        'imported': bool(state.get('fingerprint')),
        'state': state,
    }


def import_seed_knowledge(force=False):
    """
    Import seed knowledge into the canonical live IntelligenceService.

    After this call, seed chunks are immediately retrievable — no restart
    is required.
    """
    if not SEED_DIR.exists():
        return {'imported': False, 'reason': 'seed directory not found', 'files': 0, 'chunks': 0}

    fp = _fingerprint()
    state = get_setting(STATE_KEY, {}) or {}

    # Use the canonical singleton to check the live store size.
    from app.services.intelligence_provider import get_intelligence
    svc = get_intelligence()
    existing = svc.rag.store.stats().get('documents', 0)
    expected = int(state.get('chunks', 0) or 0)

    if state.get('fingerprint') == fp and not force and existing >= expected and expected > 0:
        return {'imported': False, 'reason': 'already imported', 'files': state.get('files', 0), 'chunks': expected}

    # Ingest into the canonical live instance so knowledge is immediately searchable.
    files = []
    chunks = 0
    for p in sorted(SEED_DIR.rglob('*')):
        if p.is_file() and p.suffix.lower() in SUPPORTED:
            result = svc.ingest(str(p))
            files.append(str(p.relative_to(BASE)))
            chunks += int(result.get('chunks', 0))

    state = {'fingerprint': fp, 'files': len(files), 'chunks': chunks, 'files_list': files}
    set_setting(STATE_KEY, state)
    add_activity('system', 'seed_knowledge_import', f'{len(files)} files, {chunks} chunks')
    return {'imported': True, 'files': len(files), 'chunks': chunks}
