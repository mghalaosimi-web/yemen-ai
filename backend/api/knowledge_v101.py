from fastapi import APIRouter, Depends, HTTPException, Query, Header, Cookie
from typing import Optional, Dict, Any, List
from app.services.ai_service import get_intelligence
from app.services.auth_service import decode_token
from backend.services.personal_knowledge_service import PersonalKnowledgeService
from backend.training.personal_context_importer import PersonalContextImporter
from app.data.database import connect

router = APIRouter(prefix="", tags=["knowledge_v101"])
personal_service = PersonalKnowledgeService()
importer = PersonalContextImporter()


def get_user_claims(authorization: Optional[str] = Header(default=None), yemen_ai_token: Optional[str] = Cookie(default=None)):
    token = None
    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Invalid authorization header")
        token = authorization[7:]
    else:
        token = yemen_ai_token
    if not token:
        raise HTTPException(401, "Authentication required")
    return decode_token(token)


def require_admin(claims=Depends(get_user_claims)):
    if claims.get("role") != "admin":
        raise HTTPException(403, "Insufficient permission")
    return claims


@router.get("/knowledge/domains")
def get_knowledge_domains(user=Depends(get_user_claims)):
    summary = personal_service.get_profile_summary()
    standard_domains = [
        "ai", "programming", "software_engineering", "mathematics",
        "research", "technology", "identity", "projects", "working_style"
    ]
    return {
        "status": "ok",
        "personal_domains": summary["domains"],
        "standard_domains": standard_domains
    }


@router.get("/knowledge/stats")
def get_knowledge_stats(user=Depends(get_user_claims)):
    intel = get_intelligence()
    h = intel.health()
    p_summary = personal_service.get_profile_summary()
    with connect() as c:
        runs_count = c.execute("SELECT COUNT(*) n FROM training_reports").fetchone()['n']
        packs_count = c.execute("SELECT COUNT(*) n FROM knowledge_packs").fetchone()['n']

    return {
        "status": "ok",
        "vector_knowledge": h.get("knowledge", {}),
        "graph_stats": h.get("knowledge_graph", {}),
        "personal_facts_total": p_summary["total_facts"],
        "knowledge_packs_count": packs_count,
        "training_reports_count": runs_count
    }


@router.get("/knowledge/search")
def search_knowledge_v101(
    q: str = Query(..., min_length=1),
    domain: Optional[str] = None,
    limit: int = 10,
    user=Depends(get_user_claims)
):
    intel = get_intelligence()
    username = user.get("sub", "owner") if isinstance(user, dict) else "owner"
    role = user.get("role", "admin") if isinstance(user, dict) else "admin"
    res = intel.chat(q, user_id=username, user_role=role)
    return {
        "query": q,
        "answer": res["answer"],
        "sources": res["sources"],
        "reasoning": res.get("reasoning", {})
    }


@router.get("/knowledge/conflicts")
def get_knowledge_conflicts(user=Depends(require_admin)):
    with connect() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM knowledge_conflicts ORDER BY id DESC").fetchall()]
    return {
        "status": "ok",
        "count": len(rows),
        "conflicts": rows
    }


@router.get("/training/runs")
def list_training_runs_v101(user=Depends(get_user_claims)):
    with connect() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM training_reports ORDER BY id DESC LIMIT 50").fetchall()]
    return {
        "status": "ok",
        "runs": rows
    }


@router.get("/personal-context/status")
def get_personal_context_status(user=Depends(get_user_claims)):
    summary = personal_service.get_profile_summary()
    st = "imported" if summary["total_facts"] > 0 else "awaiting_source"
    return {
        "status": st,
        "total_facts": summary["total_facts"],
        "domains": summary["domains"]
    }


@router.post("/personal-context/import")
def import_personal_context(
    payload: Dict[str, Any],
    user=Depends(require_admin)
):
    source_path = payload.get("source_path")
    content = payload.get("content")
    source_id = payload.get("source_id", "master_context")

    res = importer.import_context(source_path=source_path, content=content, source_id=source_id)
    return res


@router.post("/intelligence/rebuild-all")
def rebuild_all_intelligence(user=Depends(require_admin)):
    intel = get_intelligence()
    # Re-discover and load seed packs
    packs = intel.pack_registry.discover_packs()
    rebuilt = 0
    for pack in packs:
        intel.pack_registry.register_pack(pack)
        rebuilt += 1

    return {
        "status": "ok",
        "message": f"Successfully registered and rebuilt {rebuilt} knowledge packs.",
        "packs_rebuilt": rebuilt
    }
