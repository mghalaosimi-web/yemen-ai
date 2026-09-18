"""Final offline reasoning, evidence and control layer."""
from __future__ import annotations
from backend.services.local_brain import normalize, tokens

class ReasoningControlService:
    OPPOSITES=[('نعم','لا'),('مسموح','غير مسموح'),('يزيد','يقل'),('دائم','مؤقت'),('true','false'),('always','never')]

    def evidence_trace(self, query, hits, limit=6):
        q=set(tokens(query)); trace=[]
        for h in (hits or [])[:limit]:
            text=h.get('text',''); terms=sorted(q & set(tokens(text)))[:10]
            trace.append({'source':h.get('metadata',{}).get('source','knowledge'),'page':h.get('metadata',{}).get('page'),
                          'score':round(float(h.get('hybrid_score',h.get('score',0))),4),'matched_concepts':terms,
                          'excerpt':text[:420]})
        return trace

    def _topic_overlap(self,a,b):
        ta=set(tokens(a)); tb=set(tokens(b));
        common=(ta & tb)-{'نعم','لا','غير','مسموح','يزيد','يقل','true','false'}
        return common

    def conflicts(self, hits):
        rows=[]
        for i,a in enumerate(hits or []):
            ta=normalize(a.get('text',''))
            for b in (hits or [])[i+1:]:
                tb=normalize(b.get('text',''))
                overlap=self._topic_overlap(a.get('text',''),b.get('text',''))
                # Opposite words alone are not enough: require a shared topic/context.
                if not overlap: continue
                for pos,neg in self.OPPOSITES:
                    if ((pos in ta and neg in tb) or (neg in ta and pos in tb)):
                        rows.append({'type':'contextual_opposition','terms':[pos,neg],'shared_context':sorted(overlap)[:8],
                                     'left':a.get('text','')[:220],'right':b.get('text','')[:220]})
                        break
        return rows[:10]

    def multi_hop_concepts(self, query, graph, limit=8):
        direct=graph.related_context(query,limit=limit)
        concepts=[]
        for row in direct:
            name=row.get('name') or row.get('label') or row.get('concept')
            if name and name not in concepts: concepts.append(name)
        return concepts[:limit]

    def expand_retrieval(self, query, graph, rag, metadata_filter=None, limit=8):
        """True second-hop retrieval: query -> graph concepts -> independent retrieval -> fusion."""
        concepts=self.multi_hop_concepts(query,graph,limit=6)
        second=[]
        for concept in concepts:
            try:
                second.extend(rag.context(concept,limit=3,min_score=0.02,metadata_filter=metadata_filter) or [])
            except Exception:
                continue
        seen=set(); fused=[]
        for h in second:
            key=(h.get('metadata',{}).get('knowledge_id'),h.get('metadata',{}).get('source'),h.get('text','')[:120])
            if key not in seen: seen.add(key); fused.append(h)
        return concepts,fused[:limit]

    def fuse_hits(self, primary, secondary, limit=10):
        seen=set(); rows=[]
        for hop,hits in ((1,primary or []),(2,secondary or [])):
            for h in hits:
                key=(h.get('metadata',{}).get('knowledge_id'),h.get('metadata',{}).get('source'),h.get('text','')[:160])
                if key in seen: continue
                seen.add(key); item=dict(h); item['reasoning_hop']=hop
                score=float(item.get('hybrid_score',item.get('score',0)) or 0)
                if hop==2: score*=0.92
                item['hybrid_score']=score; rows.append(item)
        return sorted(rows,key=lambda x:float(x.get('hybrid_score',x.get('score',0)) or 0),reverse=True)[:limit]

    def should_abstain(self, confidence, hits, conflicts):
        if not hits: return True
        if confidence < 0.18: return True
        if conflicts and confidence < 0.45: return True
        return False

    def calibrate(self, base, hits, conflicts, evidence_count):
        top=float((hits or [{}])[0].get('hybrid_score',(hits or [{}])[0].get('score',0)) or 0)
        evidence=min(1.0,evidence_count/4)
        diversity=min(1.0,len({h.get('metadata',{}).get('source','') for h in (hits or [])})/3)
        score=max(0.0,min(1.0,0.40*float(base or 0)+0.30*top+0.20*evidence+0.10*diversity))
        if conflicts: score*=0.72
        if evidence_count==0: score=min(score,0.20)
        return round(score,2)

    def audit(self, intelligence):
        stats=intelligence.rag.store.stats(); graph=intelligence.graph.overview(100).get('stats',{})
        return {'status':'ok','offline':True,'knowledge_index':stats,'knowledge_graph':graph,
                'controls':['evidence_trace','contextual_conflict_detection','confidence_calibration','two_hop_retrieval','relevance_memory','abstention'],
                'recommendation':'Validate/rebuild the index after bulk imports; inspect evidence traces for low-confidence answers.'}
