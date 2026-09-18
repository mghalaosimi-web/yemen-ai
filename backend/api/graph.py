from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.api.routes import get_claims, require
from app.services.intelligence_provider import get_intelligence

router = APIRouter(prefix='/api/graph', tags=['knowledge-graph'])


class GraphText(BaseModel):
    text: str = Field(min_length=1, max_length=100000)
    source_ref: str = Field(default='manual', max_length=500)


@router.get('/overview')
def overview(limit: int = 300, claims=Depends(get_claims)):
    return get_intelligence().graph.overview(max(1, min(limit, 1000)))


@router.get('/search')
def search(q: str, limit: int = 20, claims=Depends(get_claims)):
    return {'results': get_intelligence().graph.related_context(q, max(1, min(limit, 100)))}


@router.post('/ingest')
def ingest(body: GraphText, claims=Depends(require('admin', 'developer', 'trainer'))):
    return get_intelligence().graph.ingest_text(body.text, body.source_ref)
