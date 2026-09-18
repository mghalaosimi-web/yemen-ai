"""
backend/services/knowledge_router.py
======================================
v10.2 Intelligent Knowledge Router & Multi-Source Retrieval Engine.

Routes queries across all available knowledge stores:
- VECTOR_STORE
- PERSONAL_KNOWLEDGE
- PROJECT_MEMORY
- CONVERSATION_MEMORY
- DOCUMENT_CONTEXT
- KNOWLEDGE_GRAPH
- BILINGUAL_CONCEPTS
- TECHNICAL_TERMINOLOGY

Performs independent multi-source retrieval, hit deduplication, security access scope enforcement, and evidence merging.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from backend.services.access_control import KnowledgeAccessContext, filter_by_access_scope
from backend.services.local_brain import normalize


@dataclass
class KnowledgeSearchPlan:
    query: str
    sources: List[str]             # List of source names to search
    priority_order: List[str]      # Source search execution order
    strict_scope: Optional[str] = None
    max_results: int = 15
    requires_evidence: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'query': self.query,
            'sources': self.sources,
            'priority_order': self.priority_order,
            'strict_scope': self.strict_scope,
            'max_results': self.max_results,
            'requires_evidence': self.requires_evidence,
        }


@dataclass
class MultiSourceRetrievalResult:
    plan: KnowledgeSearchPlan
    searched_sources: List[str]
    hits: List[Dict[str, Any]]
    results_per_source: Dict[str, int]
    top_evidence: List[Dict[str, Any]]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'plan': self.plan.to_dict(),
            'searched_sources': self.searched_sources,
            'results_per_source': self.results_per_source,
            'final_evidence_count': len(self.hits),
            'top_evidence': self.top_evidence[:5],
            'confidence': self.confidence,
        }


class KnowledgeRouter:
    """Intelligent multi-source knowledge routing and evidence fusion service."""

    def plan_search(
        self,
        query: str,
        task_type: str,
        intent: str,
        active_document: Optional[str] = None,
        user_id: str = 'owner'
    ) -> KnowledgeSearchPlan:
        query_lower = query.lower()
        norm = normalize(query)

        sources = []
        priority = []

        # 1. Document Mode (Strict Document Context)
        if active_document or task_type == 'DOCUMENT_QUESTION':
            sources = ['DOCUMENT_CONTEXT', 'TECHNICAL_TERMINOLOGY']
            priority = ['DOCUMENT_CONTEXT', 'TECHNICAL_TERMINOLOGY']
            return KnowledgeSearchPlan(
                query=query,
                sources=sources,
                priority_order=priority,
                strict_scope='document',
                max_results=10,
                requires_evidence=True
            )

        # 2. Personal Context Question
        if task_type == 'PERSONAL_QUESTION' or any(x in norm for x in ['عني', 'تفضيلاتي', 'سيرتي', 'اسمي']):
            sources = ['PERSONAL_KNOWLEDGE', 'CONVERSATION_MEMORY', 'VECTOR_STORE']
            priority = ['PERSONAL_KNOWLEDGE', 'CONVERSATION_MEMORY', 'VECTOR_STORE']

        # 3. Project Knowledge Question
        elif task_type == 'PROJECT_QUESTION' or any(x in norm for x in ['yemen ai', 'المشروع', 'النسخة', 'الإصدار', 'v9', 'v10']):
            sources = ['PROJECT_MEMORY', 'VECTOR_STORE', 'KNOWLEDGE_GRAPH', 'CONVERSATION_MEMORY']
            priority = ['PROJECT_MEMORY', 'VECTOR_STORE', 'KNOWLEDGE_GRAPH', 'CONVERSATION_MEMORY']

        # 4. Technical / Conceptual / General Knowledge
        else:
            sources = [
                'VECTOR_STORE',
                'TECHNICAL_TERMINOLOGY',
                'BILINGUAL_CONCEPTS',
                'KNOWLEDGE_GRAPH',
                'PROJECT_MEMORY',
                'CONVERSATION_MEMORY'
            ]
            priority = [
                'VECTOR_STORE',
                'TECHNICAL_TERMINOLOGY',
                'BILINGUAL_CONCEPTS',
                'KNOWLEDGE_GRAPH',
                'PROJECT_MEMORY',
                'CONVERSATION_MEMORY'
            ]

        return KnowledgeSearchPlan(
            query=query,
            sources=sources,
            priority_order=priority,
            max_results=15,
            requires_evidence=True
        )

    def execute_retrieval(
        self,
        service: Any,  # IntelligenceService instance
        plan: KnowledgeSearchPlan,
        access_context: KnowledgeAccessContext,
        history: List[Dict[str, Any]],
        memories: List[Dict[str, Any]],
        active_document: Optional[str] = None
    ) -> MultiSourceRetrievalResult:
        searched_sources = []
        results_per_source = {}
        all_hits = []
        seen_texts = set()

        doc_filter = ({'document_id': active_document} if active_document else None)

        for src in plan.priority_order:
            searched_sources.append(src)
            source_hits = []

            try:
                # ── Source 1: DOCUMENT_CONTEXT
                if src == 'DOCUMENT_CONTEXT' and active_document:
                    raw = service.rag.context(plan.query, limit=10, min_score=0.01, metadata_filter=doc_filter)
                    for item in raw:
                        source_hits.append({
                            'text': item.get('text', ''),
                            'hybrid_score': float(item.get('hybrid_score', item.get('score', 0.85))),
                            'metadata': {**item.get('metadata', {}), 'source': 'document_context', 'owner_scope': 'private', 'owner': access_context.user_id}
                        })

                # ── Source 2: PROJECT_MEMORY
                elif src == 'PROJECT_MEMORY':
                    proj_hist = service.project_memory.get_project_history("yemen_ai")
                    if proj_hist and proj_hist.get("state"):
                        st = proj_hist["state"]
                        proj_hit_text = (
                            f"مشروع: {st.get('name')} | النسخة الحالية: {st.get('current_version')} | "
                            f"الوصف: {st.get('description')} | التحديثات الأخيرة: {', '.join(proj_hist.get('recent_milestones', []))}"
                        )
                        source_hits.append({
                            'text': proj_hit_text,
                            'hybrid_score': 0.95,
                            'metadata': {'source': 'project_memory', 'owner_scope': 'public'}
                        })

                # ── Source 3: PERSONAL_KNOWLEDGE
                elif src == 'PERSONAL_KNOWLEDGE':
                    p_items = service.personal_knowledge.search_personal_context(plan.query, access_context.user_id, limit=5)
                    for p in p_items:
                        p_text = f"معلومة شخصية للمستخدم [{p.get('category')}]: {p.get('content')}"
                        source_hits.append({
                            'text': p_text,
                            'hybrid_score': 0.90,
                            'metadata': {'source': 'personal_knowledge', 'owner_scope': 'private', 'owner': access_context.user_id}
                        })

                # ── Source 4: TECHNICAL_TERMINOLOGY
                elif src == 'TECHNICAL_TERMINOLOGY':
                    term_info = service.terminology.lookup(plan.query)
                    if term_info and term_info.get('found'):
                        t_text = f"مصطلح تقني: {term_info.get('term')} | التعريف: {term_info.get('arabic_definition') or term_info.get('english_definition')}"
                        source_hits.append({
                            'text': t_text,
                            'hybrid_score': 0.88,
                            'metadata': {'source': 'technical_terminology', 'owner_scope': 'public'}
                        })

                # ── Source 5: BILINGUAL_CONCEPTS
                elif src == 'BILINGUAL_CONCEPTS':
                    mapping = service.concept_mapper.map_concept(plan.query)
                    if mapping and mapping.get('primary_concept'):
                        c_text = f"مفهوم ثنائي اللغة: {mapping.get('primary_concept')} | المترادفات: {', '.join(mapping.get('synonyms', []))}"
                        source_hits.append({
                            'text': c_text,
                            'hybrid_score': 0.82,
                            'metadata': {'source': 'bilingual_concepts', 'owner_scope': 'public'}
                        })

                # ── Source 6: VECTOR_STORE
                elif src == 'VECTOR_STORE':
                    raw = service.rag.context(plan.query, limit=8, min_score=0.03, metadata_filter=doc_filter)
                    for item in raw:
                        source_hits.append({
                            'text': item.get('text', ''),
                            'hybrid_score': float(item.get('hybrid_score', item.get('score', 0.50))),
                            'metadata': item.get('metadata', {})
                        })

                # ── Source 7: KNOWLEDGE_GRAPH
                elif src == 'KNOWLEDGE_GRAPH':
                    related_concepts, second_hop = service.control.expand_retrieval(plan.query, service.graph, service.rag, metadata_filter=doc_filter, limit=5)
                    for item in second_hop:
                        source_hits.append({
                            'text': item.get('text', ''),
                            'hybrid_score': float(item.get('hybrid_score', 0.45)),
                            'metadata': {**item.get('metadata', {}), 'graph_expanded': True}
                        })

                # ── Source 8: CONVERSATION_MEMORY
                elif src == 'CONVERSATION_MEMORY':
                    for mem in memories[-3:]:
                        m_text = f"ذاكرة سابقة: {mem.get('content')}"
                        source_hits.append({
                            'text': m_text,
                            'hybrid_score': 0.70,
                            'metadata': {'source': 'conversation_memory', 'owner_scope': 'private'}
                        })

            except Exception:
                pass

            # Security access filtering
            source_hits = filter_by_access_scope(source_hits, access_context)
            results_per_source[src] = len(source_hits)

            # Deduplication & score fusion
            for hit in source_hits:
                txt_norm = normalize(hit.get('text', ''))[:150]
                if txt_norm and txt_norm not in seen_texts:
                    seen_texts.add(txt_norm)
                    all_hits.append(hit)

        # Sort all hits by hybrid score descending
        all_hits.sort(key=lambda x: x.get('hybrid_score', 0.0), reverse=True)
        top_hits = all_hits[:plan.max_results]

        top_confidence = top_hits[0].get('hybrid_score', 0.10) if top_hits else 0.05

        return MultiSourceRetrievalResult(
            plan=plan,
            searched_sources=searched_sources,
            hits=top_hits,
            results_per_source=results_per_source,
            top_evidence=top_hits[:5],
            confidence=float(top_confidence)
        )
