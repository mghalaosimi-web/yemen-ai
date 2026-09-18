"""v9.0 Evidence-grounded research operations for uploaded documents."""
from __future__ import annotations
from collections import defaultdict
from backend.services.document_workspace import _terms, _sentences, _norm

class DocumentResearch:
    def __init__(self, store): self.store=store
    def _owned(self, did, owner):
        return [x for x in self.store.items if x.get('metadata',{}).get('document_id')==did and x.get('metadata',{}).get('owner')==owner]
    def _pages(self, items):
        out=defaultdict(list)
        for x in items: out[x.get('metadata',{}).get('page',1)].append(x.get('text',''))
        return out
    def _filename(self, items): return items[0].get('metadata',{}).get('source','document') if items else 'document'
    def summary(self, did, owner, max_points=8):
        items=self._owned(did,owner)
        if not items:return None
        pages=self._pages(items); selected=[]; seen=set()
        for page in sorted(pages):
            text=' '.join(pages[page]); sents=_sentences(text)
            if not sents: continue
            # Prefer informative, moderately sized sentences.
            scored=sorted(sents,key=lambda s:(len(_terms(s)), -abs(len(s)-180)),reverse=True)
            for s in scored:
                key=_norm(s)
                if key not in seen:
                    seen.add(key); selected.append({'text':s[:600],'page':page}); break
        if len(selected)>max_points:
            # Evenly cover the document rather than only its beginning.
            idx=[round(i*(len(selected)-1)/(max_points-1)) for i in range(max_points)] if max_points>1 else [0]
            selected=[selected[i] for i in dict.fromkeys(idx)]
        return {'document_id':did,'filename':self._filename(items),'summary':selected[:max_points],'grounded_only':True,'pages':len(pages)}
    def key_points(self,did,owner,limit=12):
        items=self._owned(did,owner)
        if not items:return None
        freq=defaultdict(int); candidates=[]
        for x in items:
            page=x.get('metadata',{}).get('page',1)
            for s in _sentences(x.get('text','')):
                terms=_terms(s)
                for t in terms: freq[t]+=1
                candidates.append((s,page,terms))
        scored=[]; seen=set()
        for s,page,ts in candidates:
            key=_norm(s)
            if key in seen: continue
            seen.add(key)
            score=sum(freq[t] for t in ts)/max(1,len(ts)) + min(len(ts),12)*0.2
            scored.append((score,s,page))
        scored.sort(reverse=True,key=lambda x:x[0])
        return {'document_id':did,'filename':self._filename(items),'key_points':[{'text':s[:600],'page':p} for _,s,p in scored[:limit]],'grounded_only':True}
    def search(self,dids,owner,query,limit=12):
        q=_terms(query); rows=[]
        for did in dids:
            items=self._owned(did,owner)
            if not items:return None
            for x in items:
                page=x.get('metadata',{}).get('page',1); fn=x.get('metadata',{}).get('source','document')
                for s in _sentences(x.get('text','')):
                    score=len(q&_terms(s))/max(1,len(q))
                    if score>0: rows.append((score,fn,did,page,s))
        rows.sort(reverse=True,key=lambda x:x[0]); out=[]; seen=set()
        for score,fn,did,page,s in rows:
            key=(did,_norm(s))
            if key in seen:continue
            seen.add(key);out.append({'document_id':did,'filename':fn,'page':page,'text':s[:700],'score':round(score,3)})
            if len(out)>=limit:break
        return {'query':query,'results':out,'grounded_only':True}
    def study_plan(self,did,owner,days=7):
        items=self._owned(did,owner)
        if not items:return None
        pages=sorted(self._pages(items)); days=max(1,min(int(days),60)); groups=[[] for _ in range(min(days,len(pages)))]
        for i,p in enumerate(pages): groups[i%len(groups)].append(p)
        plan=[]
        for i,g in enumerate(groups,1):
            text=' '.join(t for p in g for t in self._pages(items)[p]); focus=next(iter(_sentences(text)), 'مراجعة محتوى الصفحات المحددة')
            plan.append({'day':i,'pages':g,'focus':focus[:240],'tasks':['اقرأ الصفحات بتركيز','استخرج المفاهيم الأساسية','اكتب ملخصًا قصيرًا','اختبر فهمك بسؤالين من المحتوى']})
        return {'document_id':did,'filename':self._filename(items),'days':len(plan),'plan':plan,'grounded_only':True}
    def quiz(self,did,owner,limit=8):
        points=self.key_points(did,owner,limit)
        if not points:return None
        questions=[]
        for i,p in enumerate(points['key_points'],1):
            text=p['text']; words=[w for w in text.split() if len(w)>3]
            subject=' '.join(words[:6]) or 'الفكرة المذكورة'
            questions.append({'id':i,'question':f'اشرح الفكرة التالية بأسلوبك: {subject} ...','answer_evidence':text,'page':p['page']})
        return {'document_id':did,'filename':points['filename'],'questions':questions,'grounded_only':True}
