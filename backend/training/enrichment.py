from __future__ import annotations
import re
from backend.services.local_brain import normalize, tokens

RELATION_PATTERNS=[
    ('definition', r'(.{2,80})\s+(?:هو|هي|يعني|تعني)\s+(.{8,220})'),
    ('causal', r'(.{2,120})\s+(?:بسبب|لأن|لان|يؤدي الي|ينتج عنه)\s+(.{5,220})'),
    ('purpose', r'(.{2,120})\s+(?:يهدف الي|تستخدم في|يستخدم في|الغرض من)\s+(.{5,220})'),
]

def sentences(text):
    out=[]
    for s in re.split(r'(?<=[.!؟?])\s+|\n+', text or ''):
        s=s.strip(' -•\t')
        if 25 <= len(s) <= 600: out.append(s)
    return out

def extract_concepts(text, limit=24):
    freq={}
    for t in tokens(text):
        if len(t)>=3: freq[t]=freq.get(t,0)+1
    return [k for k,_ in sorted(freq.items(), key=lambda kv:(-kv[1],kv[0]))[:limit]]

def extract_relations(text, limit=12):
    rel=[]
    for s in sentences(text):
        ns=normalize(s)
        for kind,pat in RELATION_PATTERNS:
            m=re.search(pat,ns)
            if m:
                rel.append({'type':kind,'subject':m.group(1).strip()[:140],'object':m.group(2).strip()[:220],'evidence':s[:500]})
                break
        if len(rel)>=limit: break
    return rel

def qa_cards(text, title, limit=8):
    out=[]; seen=set()
    for s in sentences(text):
        ns=normalize(s)
        variants=[]
        if 'هو' in ns or 'هي' in ns or 'يعني' in ns or 'تعني' in ns:
            variants += [f'ما المقصود بـ {title}؟', f'عرّف {title}.']
        if any(x in ns for x in ['بسبب','لأن','لان','يؤدي الى','ينتج عنه']):
            variants += [f'لماذا يحدث ما يتعلق بـ {title}؟']
        if any(x in ns for x in ['يستخدم','تستخدم','خطوات','اولا','ثم']):
            variants += [f'كيف يتم أو يستخدم {title}؟']
        if not variants: variants=[f'ما أهم معلومة عن {title}؟']
        for q in variants:
            key=normalize(q+' '+s)
            if key not in seen:
                seen.add(key); out.append((q,s))
                if len(out)>=limit:return out
    return out
