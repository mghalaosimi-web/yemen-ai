"""v8.9 Document Research Workspace: evidence-first document operations."""
from __future__ import annotations
import re
from collections import defaultdict

AR_STOP={'في','من','على','الى','إلى','عن','ما','ماذا','هذا','هذه','ذلك','التي','الذي','ثم','او','أو','و','يا','مع','كل','كان','تكون','كيف','لماذا','لم','لا','ان','إن','قد','حتى'}

def _norm(text):
    text=str(text or '').lower()
    text=re.sub(r'[إأآا]','ا',text); text=re.sub('ى','ي',text); text=re.sub('ة','ه',text)
    return re.sub(r'[^\w\s]',' ',text)

def _terms(text): return {x for x in _norm(text).split() if len(x)>2 and x not in AR_STOP}

def _sentences(text):
    out=[]
    for s in re.split(r'(?<=[.!؟?])\s+|\n+',str(text or '')):
        s=s.strip(' -•\t')
        if 30<=len(s)<=600: out.append(s)
    return out

class DocumentWorkspace:
    def __init__(self, store): self.store=store

    def owned(self, document_id, owner):
        return [x for x in self.store.items if x.get('metadata',{}).get('document_id')==document_id and x.get('metadata',{}).get('owner')==owner]

    def list_documents(self, owner):
        groups=defaultdict(list)
        for x in self.store.items:
            m=x.get('metadata',{})
            if m.get('owner')==owner and m.get('document_id'): groups[m['document_id']].append(x)
        result=[]
        for did,items in groups.items():
            m=items[0].get('metadata',{}); pages=sorted({x.get('metadata',{}).get('page') for x in items if x.get('metadata',{}).get('page')})
            result.append({'document_id':did,'filename':m.get('source','document'),'chunks':len(items),'pages':len(pages),'ocr_pages':sorted({x.get('metadata',{}).get('page') for x in items if x.get('metadata',{}).get('ocr')})})
        return sorted(result,key=lambda x:x['filename'].lower())

    def outline(self, document_id, owner, limit=20):
        items=self.owned(document_id,owner)
        if not items: return None
        by_page=defaultdict(list)
        for x in items: by_page[x.get('metadata',{}).get('page',1)].append(x.get('text',''))
        sections=[]
        for page in sorted(by_page):
            text=' '.join(by_page[page])
            candidates=_sentences(text)
            if not candidates: continue
            # Prefer heading-like short sentences, otherwise first informative sentence.
            heading=next((s for s in candidates if len(s)<140 and (s.endswith(':') or re.match(r'^(الفصل|الباب|المبحث|chapter|section|\d+[.)])',s,re.I))), candidates[0])
            sections.append({'page':page,'summary':heading[:280]})
            if len(sections)>=limit: break
        m=items[0].get('metadata',{})
        return {'document_id':document_id,'filename':m.get('source'),'pages':len(by_page),'outline':sections,'strict_source':True}

    def compare(self, document_ids, owner, question):
        if len(document_ids)<2: return None
        q=_terms(question); rows=[]
        for did in document_ids[:5]:
            items=self.owned(did,owner)
            if not items: return None
            best=[]
            for item in items:
                for s in _sentences(item.get('text','')):
                    score=len(q & _terms(s))/max(1,len(q)) if q else 0
                    if score>0: best.append((score,s,item.get('metadata',{}).get('page')))
            best.sort(key=lambda x:x[0],reverse=True)
            # Distinct evidence snippets only.
            evidence=[]; seen=set()
            for score,s,page in best:
                key=_norm(s)
                if key in seen: continue
                seen.add(key); evidence.append({'text':s,'page':page,'score':round(score,3)})
                if len(evidence)>=3: break
            m=items[0].get('metadata',{})
            rows.append({'document_id':did,'filename':m.get('source'),'evidence':evidence})
        return {'question':question,'documents':rows,'grounded_only':True,'note':'المقارنة تعرض أدلة منفصلة من كل مستند ولا تضيف معلومات من خارج المستندات المحددة.'}
