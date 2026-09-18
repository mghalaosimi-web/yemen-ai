from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from app.services.intelligence_provider import get_intelligence
from app.api.routes import get_claims, require
from app.core.config import UPLOAD_DIR
from app.data.database import (
    conversation_history, clear_conversation,
    recent_memories, clear_memories,
    add_answer_feedback, memory_stats,
    list_knowledge,
)

router = APIRouter(prefix='/api/intelligence', tags=['intelligence'])


def _svc():
    """Return the canonical singleton IntelligenceService."""
    return get_intelligence()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    session_id: str = Field(default='default', min_length=1, max_length=128)

class IngestRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=512)

class FeedbackRequest(BaseModel):
    session_id: str = Field(default='default', min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=12000)
    answer: str = Field(min_length=1, max_length=24000)
    rating: int = Field(ge=1, le=5)
    notes: str = Field(default='', max_length=2000)


@router.get('/health')
def health(claims=Depends(get_claims)):
    return _svc().health()


@router.post('/chat')
def chat(body: ChatRequest, claims=Depends(get_claims)):
    return _svc().chat(body.message, body.session_id)


@router.get('/memory/{session_id}')
def memory(session_id: str, claims=Depends(get_claims)):
    return {
        'session_id': session_id,
        'history': conversation_history(session_id, 50),
        'memories': recent_memories(session_id, 50),
        'stats': memory_stats(session_id),
    }


@router.delete('/memory/{session_id}')
def forget(session_id: str, claims=Depends(get_claims)):
    return {
        'cleared_messages': clear_conversation(session_id),
        'cleared_memories': clear_memories(session_id),
    }


@router.post('/feedback')
def feedback(body: FeedbackRequest, claims=Depends(get_claims)):
    fid = add_answer_feedback(body.session_id, body.message, body.answer, body.rating, body.notes)
    return {'id': fid, 'status': 'recorded'}


@router.post('/ingest')
def ingest(body: IngestRequest, claims=Depends(require('admin', 'developer', 'trainer'))):
    filename = Path(body.filename).name
    path = (UPLOAD_DIR / filename).resolve()
    root = UPLOAD_DIR.resolve()
    if root not in path.parents or not path.exists() or not path.is_file():
        raise HTTPException(404, detail='Uploaded file not found')
    try:
        return _svc().ingest(str(path))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.get('/audit')
def audit(claims=Depends(require('admin', 'developer', 'trainer'))):
    return _svc().control.audit(_svc())


@router.post('/rebuild-index')
def rebuild_index(claims=Depends(require('admin', 'developer'))):
    """Reload the vector store from disk (for multi-process deployments)."""
    _svc().rag.store.sync_from_disk()
    return {'status': 'reloaded', 'knowledge': _svc().rag.store.stats()}


@router.post('/rebuild-from-db')
def rebuild_from_db(claims=Depends(require('admin', 'developer'))):
    """
    Recover the vector store from SQLite knowledge records.

    Use this when vector_store.json is missing or empty but the SQLite
    knowledge table is intact.  The endpoint is idempotent — the store's
    built-in deduplication prevents duplicate chunks.
    """
    svc = _svc()
    items = list_knowledge()
    scanned = len(items)
    chunks_created = 0
    duplicates_skipped = 0
    failures = []

    for item in items:
        try:
            text = str(item.get('content', '') or '').strip()
            if not text:
                continue
            from backend.rag.chunker import chunk_text
            for chunk in chunk_text(text):
                before = len(svc.rag.store.items)
                svc.rag.store.add(chunk, {
                    'source': item.get('source', 'manual'),
                    'knowledge_id': item['id'],
                    'title': item.get('title', ''),
                    'training_artifact': 'recovered_knowledge',
                })
                after = len(svc.rag.store.items)
                if after > before:
                    chunks_created += 1
                else:
                    duplicates_skipped += 1
        except Exception as exc:
            failures.append({'id': item.get('id'), 'error': str(exc)[:200]})

    # Also rebuild graph from recovered knowledge
    for item in items:
        try:
            svc.graph.ingest_text(
                str(item.get('content', '')),
                source_ref=f"db_recovery:{item['id']}"
            )
        except Exception:
            pass

    return {
        'status': 'completed',
        'knowledge_items_scanned': scanned,
        'chunks_created': chunks_created,
        'duplicates_skipped': duplicates_skipped,
        'failures': failures,
        'knowledge_index': svc.rag.store.stats(),
    }
