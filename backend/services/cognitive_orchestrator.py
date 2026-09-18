"""v8.6 Adaptive Cognitive Orchestrator.
A deterministic offline planning layer: resolve context, select evidence, detect conflicts,
rank memories and build an answer plan before the local brain writes the response.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from backend.services.local_brain import normalize, tokens

REFERENTIAL = {'هذا','هذه','ذلك','تلك','الموضوع','النقطة','الجزء','الذي قلته','اللي قلته','هذي','هاذا'}
FOLLOWUPS = {'اشرح اكثر','وضح اكثر','كمل','تابع','واصل','فصل اكثر','اعطني مثال','مثال'}

@dataclass
class CognitivePlan:
    original: str
    resolved: str
    query: str
    mode: str
    subgoals: list[str]
    context_used: bool
    memory_used: bool
    conflict: bool=False

class CognitiveOrchestrator:
    def _last_user_topic(self, history):
        for row in reversed(history or []):
            if row.get('role')=='user' and len(row.get('content','').strip())>8:
                return row['content'].strip()
        return ''

    def resolve_context(self, message, history):
        n=normalize(message)
        last=self._last_user_topic(history)
        short=len(tokens(message))<=5
        referential=any(x in n for x in REFERENTIAL) or n in FOLLOWUPS
        if last and short and referential:
            if any(x in n for x in {'اشرح','وضح','فصل','مثال'}):
                return f'{message} بخصوص: {last}', True
            if n in {'تابع','كمل','واصل'}:
                return f'تابع شرح الموضوع السابق: {last}', True
        return message, False

    def mode(self, message):
        n=normalize(message)
        if any(x in n for x in ['خطوات','كيف ابدا','كيف ابدأ','كيف اسوي','كيف افعل']): return 'plan'
        if any(x in n for x in ['قارن','الفرق بين','مقارنة']): return 'compare'
        if any(x in n for x in ['لخص','اختصر','ملخص']): return 'summary'
        if any(x in n for x in ['لماذا','ليش','سبب']): return 'causal'
        if any(x in n for x in ['اشرح','وضح','فصل','بالتفصيل']): return 'deep_explain'
        return 'answer'

    def subgoals(self, mode):
        return {
            'plan':['فهم الهدف','ترتيب الخطوات','إضافة نقطة تحقق'],
            'compare':['تحديد العناصر','استخراج الفروق','صياغة خلاصة'],
            'summary':['استخراج الأفكار','حذف التكرار','ضغط المعنى'],
            'causal':['تحديد الظاهرة','البحث عن السبب','ربط السبب بالنتيجة'],
            'deep_explain':['تعريف','آلية العمل','مثال','خلاصة'],
        }.get(mode,['فهم السؤال','استرجاع الأدلة','صياغة الإجابة'])

    def relevant_memories(self, message, memories, limit=4):
        q=set(tokens(message)); ranked=[]
        for m in memories or []:
            content=m.get('content',''); mt=set(tokens(content))
            overlap=len(q & mt)/max(1,len(q))
            importance=float(m.get('importance',0.5) or 0.5)
            score=overlap*0.72+importance*0.28
            if overlap>0: ranked.append((score,m))
        ranked.sort(key=lambda x:x[0],reverse=True)
        return [m for _,m in ranked[:limit]]

    def detect_conflict(self, hits):
        # Conservative: only flag obvious opposite markers among strong evidence.
        texts=' '.join((h.get('text') or '')[:1200] for h in (hits or [])[:5]).lower()
        pairs=[('نعم','لا'),('يزيد','يقل'),('مسموح','غير مسموح')]
        return any(a in texts and b in texts for a,b in pairs)

    def build(self, message, history, memories, hits):
        resolved,ctx=self.resolve_context(message,history)
        mode=self.mode(resolved)
        rm=self.relevant_memories(resolved,memories)
        return CognitivePlan(message,resolved,resolved,mode,self.subgoals(mode),ctx,bool(rm),self.detect_conflict(hits)), rm
