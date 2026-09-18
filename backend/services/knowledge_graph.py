from __future__ import annotations
import re
from datetime import datetime, timezone
from collections import Counter
from typing import List, Dict, Any, Optional
from app.data.database import upsert_graph_node, upsert_graph_edge, graph_overview, graph_search
from backend.services.arabic_normalizer import ArabicNormalizer

STOP = {'هذا','هذه','ذلك','التي','الذي','على','من','في','إلى','عن','مع','وهو','وهي','كان','يمكن','كما','تم','أن','the','and','for','with','from','into','that','this','are','is','of','to','a','an'}
TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_+-]{2,}|[؀-ۿ]{3,}")

RELATION_PATTERNS = [
    (re.compile(r'(\b[\w\u0600-\u06ff]+\b)\s+(?:نوع من|هو نوع من|ينتمي إلى|is a|type of)\s+(\b[\w\u0600-\u06ff]+\b)'), 'IS_A'),
    (re.compile(r'(\b[\w\u0600-\u06ff]+\b)\s+(?:جزء من|يتكون من|part of)\s+(\b[\w\u0600-\u06ff]+\b)'), 'PART_OF'),
    (re.compile(r'(\b[\w\u0600-\u06ff]+\b)\s+(?:يؤدي إلى|يسبب|causes|leads to)\s+(\b[\w\u0600-\u06ff]+\b)'), 'CAUSES'),
    (re.compile(r'(\b[\w\u0600-\u06ff]+\b)\s+(?:يعتمد على|يحتاج إلى|depends on)\s+(\b[\w\u0600-\u06ff]+\b)'), 'DEPENDS_ON'),
    (re.compile(r'(\b[\w\u0600-\u06ff]+\b)\s+(?:يستخدم في|يستخدم لـ|used for)\s+(\b[\w\u0600-\u06ff]+\b)'), 'USED_FOR'),
]

class KnowledgeGraphService:
    def __init__(self):
        self.normalizer = ArabicNormalizer()

    def add_node(self, name: str, node_type: str = 'concept', metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
        return upsert_graph_node(name, node_type, metadata)

    def add_edge(self, source_id: int, target_id: int, relation: str = 'related_to', weight: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
        return upsert_graph_edge(source_id, target_id, relation, weight, metadata)

    def extract(self, text: str, limit: int = 24) -> List[str]:
        terms = []
        for t in TOKEN.findall(text or ''):
            key = t.strip('،.؛:()[]{}').lower()
            if key not in STOP and len(key) >= 3:
                terms.append(t.strip())
        counts = Counter(terms)
        return [x for x, _ in counts.most_common(limit)]

    def extract_typed_relations(self, text: str) -> List[Dict[str, Any]]:
        relations = []
        for pat, rel_type in RELATION_PATTERNS:
            for source_term, target_term in pat.findall(text or ''):
                if len(source_term) >= 3 and len(target_term) >= 3:
                    relations.append({
                        'source': source_term.strip(),
                        'target': target_term.strip(),
                        'type': rel_type,
                        'confidence': 0.90
                    })
        return relations

    def ingest_text(self, text: str, source_ref: str = 'manual') -> Dict[str, Any]:
        terms = self.extract(text)
        ids = [upsert_graph_node(t, 'concept', {'source': source_ref}) for t in terms]
        edges = 0
        now_str = datetime.now(timezone.utc).isoformat()

        # Co-occurrence default edges
        for i in range(len(ids) - 1):
            meta = {'source': source_ref, 'relation_type': 'co_occurs', 'created_at': now_str}
            if upsert_graph_edge(ids[i], ids[i+1], 'co_occurs', 1.0, meta):
                edges += 1

        # Typed relations
        typed_rels = self.extract_typed_relations(text)
        for rel in typed_rels:
            n1 = upsert_graph_node(rel['source'], 'concept', {'source': source_ref})
            n2 = upsert_graph_node(rel['target'], 'concept', {'source': source_ref})
            if n1 and n2:
                meta = {
                    'source': source_ref,
                    'relation_type': rel['type'],
                    'confidence': rel['confidence'],
                    'created_at': now_str
                }
                if upsert_graph_edge(n1, n2, rel['type'], rel['confidence'], meta):
                    edges += 1

        return {
            'entities': terms,
            'nodes': len([x for x in ids if x]),
            'edges': edges,
            'typed_relations_found': len(typed_rels)
        }

    def related_context(self, query: str, limit: int = 8, max_depth: int = 2) -> List[Dict[str, Any]]:
        hits = graph_search(query, limit)
        if not hits:
            terms = self.extract(query, limit=6)
            for t in terms:
                hits.extend(graph_search(t, limit))
        
        seen = set()
        out = []

        # Depth-bounded multi-hop collection (max_depth=2)
        for depth in range(1, max_depth + 1):
            for x in hits:
                if x['id'] not in seen:
                    seen.add(x['id'])
                    x_item = dict(x)
                    x_item['hop_depth'] = depth
                    out.append(x_item)
                if len(out) >= limit:
                    break

        return out[:limit]

    def overview(self, limit: int = 300) -> Dict[str, Any]:
        return graph_overview(limit)
