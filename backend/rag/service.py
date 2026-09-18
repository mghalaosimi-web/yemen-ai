from __future__ import annotations
import re
import math
from collections import Counter
from typing import List, Dict, Any, Optional
from .store import JsonVectorStore
from .ingest import ingest_file
from backend.services.local_brain import LocalReasoningEngine
from backend.services.arabic_normalizer import ArabicNormalizer
from backend.services.semantic_expander import SemanticQueryExpander
from backend.rag.retrieval_config import DEFAULT_RETRIEVAL_CONFIG, EvidenceScore
from backend.rag.reranker import get_default_reranker

def _norm(text):
    normalizer = ArabicNormalizer()
    return normalizer.normalize(text).search_tokens

class RAGService:
    def __init__(self, store=None):
        self.store = store or JsonVectorStore()
        self.normalizer = ArabicNormalizer()
        self.expander = SemanticQueryExpander()
        self.reranker = get_default_reranker()

    def ingest(self, path, metadata_base=None):
        return ingest_file(path, self.store, metadata_base=metadata_base)

    def context(self, query: str, limit: int = 5, min_score: float = 0.05, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        # 1. Arabic-aware normalization & local brain query expansion
        raw_norm = self.normalizer.normalize(query)
        brain_exp = LocalReasoningEngine().expand_query(query)
        semantic_exp = self.expander.expand(query)
        
        expanded_terms = dict.fromkeys([
            query,
            raw_norm.normalized_text,
            *raw_norm.light_stems,
            *brain_exp,
            *[e.term for e in semantic_exp if e.confidence >= 0.75]
        ])
        expanded_query = ' '.join(expanded_terms)

        metadata_filter = dict(metadata_filter or {})
        candidates = [
            x for x in self.store.items
            if all(x.get('metadata', {}).get(k) == v for k, v in metadata_filter.items())
        ]
        if not candidates:
            return []

        # 2. Stage 1 Retrieval: Vector Candidate Search
        vector_hits = {
            h['text']: h for h in self.store.search(expanded_query, max(limit * 6, 30), items=candidates)
        }

        # BM25 Lexical Calculation
        q_tokens = _norm(expanded_query)
        qs = set(q_tokens)
        N = len(candidates)
        df = Counter()
        docs = []
        for item in candidates:
            ts = set(_norm(item.get('text', '')))
            docs.append((item, ts))
            for t in ts:
                df[t] += 1

        lexical_hits = {}
        for item, ts in docs:
            common = qs & ts
            if not common:
                continue
            bm25_val = sum(math.log((N + 1) / (df[t] + 1)) + 1 for t in common) / max(1, sum(math.log((N + 1) / (df[t] + 1)) + 1 for t in qs))
            phrase = ' '.join(q_tokens) in ' '.join(_norm(item.get('text', '')))
            lex_score = min(1.0, bm25_val + (0.12 if phrase else 0.0))
            lexical_hits[item['text']] = {
                'score': lex_score,
                'text': item['text'],
                'metadata': item.get('metadata', {})
            }

        # 3. Stage 2 Candidate Merging & Multi-Signal Evidence Scoring
        all_candidate_texts = set(vector_hits) | set(lexical_hits)
        candidate_objects = []

        for text in all_candidate_texts:
            v_score = float(vector_hits.get(text, {}).get('score', 0.0))
            l_score = float(lexical_hits.get(text, {}).get('score', 0.0))
            base_item = vector_hits.get(text) or lexical_hits.get(text)
            meta = dict(base_item.get('metadata', {}))

            ev_score = EvidenceScore(
                semantic_score=v_score,
                lexical_score=l_score,
                source_quality_score=0.9 if meta.get('source') == 'user_document' else 0.8
            )
            final_sc = ev_score.compute_final(DEFAULT_RETRIEVAL_CONFIG)

            candidate_objects.append({
                'id': base_item.get('id'),
                'text': text,
                'metadata': meta,
                'score': final_sc,
                'hybrid_score': final_sc,
                'vector_score': round(v_score, 4),
                'lexical_score': round(l_score, 4),
                'evidence_scores': ev_score.to_dict(),
                'provenance': {
                    'knowledge_id': meta.get('knowledge_id'),
                    'document_id': meta.get('document_id'),
                    'source': meta.get('source', 'knowledge'),
                    'training_run_id': meta.get('training_run_id')
                }
            })

        # 4. Stage 3 Deduplication
        candidate_objects.sort(key=lambda h: h['score'], reverse=True)
        unique_candidates = []
        seen_fps = set()
        for cand in candidate_objects:
            fp = cand.get('metadata', {}).get('content_fp') or cand['text'].strip()[:80]
            if fp not in seen_fps:
                seen_fps.add(fp)
                unique_candidates.append(cand)

        # 5. Stage 4 Second-Stage Reranking
        top_candidates = unique_candidates[:max(limit * 4, 15)]
        reranked = self.reranker.rerank(query, top_candidates, limit=limit)

        return [h for h in reranked if h['score'] >= min_score]

    def answer_prompt(self, question: str, limit: int = 5):
        hits = self.context(question, limit)
        context = '\n\n'.join(
            f"[Source: {h['metadata'].get('source', 'knowledge')}]\n{h['text']}" for h in hits
        ) if hits else 'No sufficiently relevant local knowledge was found.'
        return f"You are Yemen AI. Use supplied evidence.\n\nKNOWLEDGE:\n{context}\n\nQUESTION:\n{question}", hits
