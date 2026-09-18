from __future__ import annotations
import ast, math, operator, re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

# v8.5 Cognitive Core: deterministic, offline, Arabic-first reasoning pipeline.
AR_STOP={"في","من","على","الى","إلى","عن","ما","ماذا","هل","هذا","هذه","ذلك","تلك","انا","أنا","انت","أنت","هو","هي","لي","ثم","او","أو","و","يا","لو","مع","كل","كان","تكون","كيف","ليش","لماذا","متى","اين","أين","اي","أي","ب","ل","ان","إن","قد","حتى","بعد","قبل","عند","الذي","التي","كما","لكن","او","أم"}
AR_ALIASES={"هاذا":"هذا","هاذه":"هذه","هاذي":"هذه","اشرحلي":"اشرح لي","اشرحلى":"اشرح لي","قللي":"قل لي","كمل":"تابع","اكمل":"تابع","ذلحين":"الآن","الحين":"الآن","ليش":"لماذا","كيفاش":"كيف","ايش":"ماذا","وش":"ماذا","ابغى":"اريد","ابي":"اريد","مابي":"لا اريد","تقولي":"تقول لي"}
SYNONYMS={
    "ذكاء":["اصطناعي","ai","تعلم","نماذج"],"برمجة":["programming","كود","code","تطوير"],
    "خوارزمية":["algorithm","خطوات","حل"],"امن":["security","سيبراني","cybersecurity","حماية"],
    "تعلم":["دراسة","learning","training","تدريب"],"بيانات":["database","sql","معلومات","db"],
    "شبكة":["network","networks"],"بايثون":["python","برمجة"],"rag":["استرجاع","معرفة","retrieval"],
}

@dataclass
class Plan:
    intent:str
    language:str
    query_terms:list[str]
    answer_style:str
    confidence:float=0.0


def normalize(text:str)->str:
    text=str(text or '').lower().strip()
    for src,dst in AR_ALIASES.items():
        text=re.sub(rf'(?<!\w){re.escape(src)}(?!\w)',dst,text)
    text=re.sub(r'[إأآا]','ا',text); text=re.sub('ى','ي',text); text=re.sub('ة','ه',text)
    text=re.sub(r'[ًٌٍَُِّْـ]','',text); text=re.sub(r'[^\w\s]',' ',text)
    return re.sub(r'\s+',' ',text).strip()

def tokens(text:str):
    return [t for t in normalize(text).split() if len(t)>1 and t not in AR_STOP]

class LocalReasoningEngine:
    """Offline cognitive pipeline: understand -> retrieve -> rank -> synthesize -> self-check.

    This is deliberately transparent about being rule/knowledge based rather than pretending to
    be a giant generative model. The goal is useful, stable local reasoning without API calls.
    """
    def detect_language(self,text):
        return 'ar' if re.search(r'[\u0600-\u06ff]',text or '') else 'en'

    def intent(self,text):
        n=normalize(text)
        if not n:return 'empty'
        patterns=[
            ('greeting',['مرحبا','اهلا','السلام عليكم','هلا','صباح الخير','مساء الخير']),
            ('identity',['من انت','عرفني بنفسك','ما انت','اسمك ايش','اسمك ماذا']),
            ('thanks',['شكرا','مشكور','تسلم','thanks','thank you']),
            ('goodbye',['وداعا','مع السلامه','باي','bye']),
            ('capabilities',['ماذا تستطيع','ماذا تقدر','ايش تقدر','قدراتك','ماذا تفعل','وش تسوي']),
            ('summarize',['لخص','اختصر','ملخص','الخلاصه']),
            ('compare',['قارن','الفرق بين','مقارنه','مقارنة','وش الفرق']),
            ('steps',['خطوات','خطوه بخطوه','خطوة بخطوة','كيف ابدا','كيف ابدأ','من اين ابدا']),
            ('why',['لماذا','ليش','السبب','لماذا يحدث']),
            ('how',['كيف يعمل','كيف اشتغل','كيف يتم','كيف اسوي','كيف افعل']),
            ('define',['ما هو','ماهو','ماهي','ما هي','تعريف','عرف لي']),
            ('explain',['وضح','اشرح','فصل','تفصيل','بالتفصيل']),
            ('continue',['نعم','تابع','استمر','هيا','واصل']),
        ]
        for name,phrases in patterns:
            if name=='goodbye':
                if any(re.search(rf'(^|\s){re.escape(p)}(\s|$)',n) for p in phrases): return name
            elif any(p in n for p in phrases): return name
        return 'question'

    def expand_query(self,question):
        base=tokens(question); n=normalize(question); extra=[]
        for key,vals in SYNONYMS.items():
            if key in n or any(v in base for v in vals): extra += [key,*vals]
        # lightweight Arabic stems improve recall without over-normalizing names
        stems=[]
        for w in base:
            if len(w)>=5:
                stems.append(w.removeprefix('ال'))
                for suf in ('ات','ون','ين','ه','ة'):
                    if w.endswith(suf) and len(w)>len(suf)+3: stems.append(w[:-len(suf)])
        return list(dict.fromkeys(base+extra+stems))[:32]

    def plan(self,message)->Plan:
        i=self.intent(message); lang=self.detect_language(message); q=self.expand_query(message)
        styles={'summarize':'summary','steps':'steps','compare':'comparison','define':'definition','explain':'explanation','why':'causal','how':'procedural'}
        return Plan(i,lang,q,styles.get(i,'direct'))

    def _score(self,question,hit):
        q=self.expand_query(question); text=tokens(hit.get('text',''))
        if not q or not text:return float(hit.get('score',0))
        qs,ts=set(q),set(text); overlap=len(qs & ts)/max(1,len(qs))
        exact=sum(1 for w in qs if w in ts and len(w)>=4)/max(1,len(qs))
        phrase=0.12 if normalize(question) in normalize(hit.get('text','')) else 0
        return float(hit.get('score',0))*0.36+overlap*0.42+exact*0.22+phrase

    def rank(self,question,hits,limit=8):
        ranked=[]
        for h in hits or []:
            x=dict(h); x['hybrid_score']=round(self._score(question,x),4); ranked.append(x)
        return sorted(ranked,key=lambda x:x['hybrid_score'],reverse=True)[:limit]

    def _clean_text(self,text):
        text=re.sub(r'#+\s*','',text or ''); text=re.sub(r'\[(Source|المصدر):[^\]]+\]','',text)
        return re.sub(r'\n{3,}','\n\n',text).strip()

    def _sentences(self,text):
        parts=re.split(r'(?<=[.!؟?])\s+|\n+',self._clean_text(text)); out=[]
        for p in parts:
            p=re.sub(r'^#+\s*','',p.strip(' -•\t')).strip()
            if len(p)<=20 or len(p)>650: continue
            if re.match(r'^(س|ج|q|a)\s*[:：]',p,re.I): continue
            if p.lower().startswith(('training example','example dialogue')): continue
            out.append(p)
        return out

    def _best_sentences(self,question,hits,max_sentences=5):
        q=set(self.expand_query(question)); candidates=[]; lang=self.detect_language(question)
        for hit in hits:
            for s in self._sentences(hit.get('text','')):
                if lang=='ar' and self.detect_language(s)!='ar': continue
                st=set(tokens(s)); overlap=len(q & st)
                if q and overlap==0: continue
                score=overlap/max(1,len(q))*0.7+float(hit.get('hybrid_score',0))*0.3
                # Prefer informative, compact sentences.
                score += max(0,0.08-abs(len(s)-220)/5000)
                candidates.append((score,s))
        candidates.sort(key=lambda x:x[0],reverse=True); out=[]; seen=set()
        for _,s in candidates:
            key=normalize(s)
            if key in seen:continue
            seen.add(key); out.append(s)
            if len(out)>=max_sentences:break
        return out

    def _history_topic(self,history):
        for row in reversed(history or []):
            if row.get('role')=='assistant' and len(row.get('content',''))>30:return row['content'][:1200]
        return ''

    def _safe_math(self,text):
        expr=re.sub(r'[^0-9+\-*/().% ]','',text)
        if not expr or not re.search(r'\d',expr) or len(expr)>80:return None
        ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Mod:operator.mod,ast.Pow:operator.pow,ast.USub:operator.neg}
        try:
            def ev(n):
                if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)):return n.value
                if isinstance(n,ast.BinOp) and type(n.op) in ops:return ops[type(n.op)](ev(n.left),ev(n.right))
                if isinstance(n,ast.UnaryOp) and type(n.op) in ops:return ops[type(n.op)](ev(n.operand))
                raise ValueError
            v=ev(ast.parse(expr,mode='eval').body)
            return v if math.isfinite(float(v)) and abs(float(v))<1e15 else None
        except Exception:return None

    def _concept_answer(self,message,intent):
        n=normalize(message)
        concepts=[
            (['اليمن'],'اليمن دولة تقع في جنوب غرب شبه الجزيرة العربية، وتتميز بتاريخ وحضارة وثقافة غنية وتنوع جغرافي كبير.'),
            (['ذكاء اصطناعي','الذكاء الاصطناعي','ai'],'الذكاء الاصطناعي مجال يبني أنظمة تستطيع التعلم أو الاستدلال أو اتخاذ قرارات ضمن مهام محددة اعتمادًا على البيانات والخوارزميات.'),
            (['تعلم اله','تعلم الي','machine learning'],'تعلم الآلة فرع من الذكاء الاصطناعي يتعلم أنماطًا من البيانات لتحسين الأداء في التصنيف والتنبؤ واتخاذ القرار.'),
            (['بايثون','python'],'بايثون لغة برمجة عالية المستوى سهلة القراءة، وتستخدم في تطوير الويب والأتمتة وتحليل البيانات والذكاء الاصطناعي.'),
            (['منهج علمي','المنهج العلمي','scientific method'],'المنهج العلمي هو أسلوب منظم يبدأ بالملاحظة والسؤال ثم الفرضية والاختبار وتحليل الأدلة ومراجعة النتائج.'),
            (['خوارزمي','algorithm'],'الخوارزمية سلسلة خطوات واضحة ومحددة لحل مشكلة، ويُنظر إلى صحتها وكفاءتها في الزمن والذاكرة.'),
            (['rag','استرجاع معزز'],'RAG أسلوب يسترجع المعرفة المرتبطة بالسؤال أولًا ثم يستخدمها لصياغة إجابة مبنية على الأدلة، وهو ليس تدريبًا لنموذج جديد من الصفر.'),
            (['تضمين','embeddings'],'التضمينات تمثيلات رقمية للنصوص أو العناصر تساعد النظام على قياس التشابه المعنوي والبحث عن المحتوى المرتبط.'),
            (['امن سيبراني','الامن السيبراني','أمن سيبراني','cybersecurity'],'الأمن السيبراني يهدف إلى حماية الأنظمة والشبكات والبيانات من الوصول غير المصرح به والتعطيل والتلاعب.'),
            (['قاعده بيانات','قاعدة بيانات','database'],'قاعدة البيانات نظام منظم لتخزين المعلومات واسترجاعها، ويشمل الجداول والعلاقات والفهارس والاستعلامات.'),
        ]
        for keys,answer in concepts:
            if any(k in n for k in keys):
                if intent=='summarize':return 'الخلاصة: '+answer
                if intent=='steps':return 'لفهم الموضوع عمليًا: 1) افهم الفكرة الأساسية. 2) شاهد مثالًا بسيطًا. 3) طبّق بنفسك. 4) اختبر النتيجة. 5) راجع أخطاءك وحسّن الحل.'
                if intent=='why':return answer+' والسبب أن هذا المجال أو المفهوم صُمم لمعالجة مشكلة محددة بطريقة منظمة وقابلة للقياس.'
                return answer
        return None

    def _synthesize(self,plan:Plan,best:list[str]):
        if plan.language!='ar':return 'Based on the local knowledge available to me:\n\n'+'\n'.join('• '+s for s in best)
        # Deduplicate semantic near-duplicates by token overlap.
        selected=[]
        for s in best:
            st=set(tokens(s))
            if any(len(st & set(tokens(x)))/max(1,len(st|set(tokens(x))))>0.72 for x in selected):continue
            selected.append(s)
        if plan.answer_style=='summary':return 'الخلاصة:\n\n'+'\n'.join('• '+s for s in selected[:3])
        if plan.answer_style in {'steps','procedural'}:return 'بشكل مرتب:\n\n'+'\n'.join(f'{i+1}. {s}' for i,s in enumerate(selected))
        if plan.answer_style=='comparison':return 'المقارنة بناءً على المعرفة المتاحة:\n\n'+'\n'.join('• '+s for s in selected)
        if plan.answer_style in {'definition','explanation','causal'}:return 'التوضيح:\n\n'+'\n'.join('• '+s for s in selected)
        return 'بحسب المعرفة المحلية المتاحة:\n\n'+'\n'.join('• '+s for s in selected)

    def _self_check(self,answer,message,language):
        if not answer:return False
        forbidden=['session context','system prompt','hidden context','memory dump']
        low=answer.lower()
        if any(x in low for x in forbidden):return False
        if language=='ar' and len(re.findall(r'[\u0600-\u06ff]',answer))<3:return False
        if normalize(answer).count(normalize(message))>3:return False
        return True

    def answer(self,message,hits=None,history=None,memories=None,grounded_only=False):
        message=(message or '').strip(); plan=self.plan(message); math_value=self._safe_math(message)
        if math_value is not None and len(tokens(message))<=3:
            return (f'الناتج: {math_value}' if plan.language=='ar' else f'Result: {math_value}'), {'intent':'calculation','confidence':1.0,'pipeline':['parse','safe_math']}
        hits=self.rank(message,hits or [])
        # Strict document-grounded mode: no canned answers, concept fallbacks or outside knowledge.
        # This guarantees that an uploaded document remains the sole evidence source.
        if grounded_only:
            best=self._best_sentences(message,hits,6)
            if not best:
                return ('لم أجد داخل المستند المرفوع دليلاً كافيًا للإجابة عن هذا السؤال. سألتزم بالمستند كمصدر ولن أضف معلومات من خارجه.' if plan.language=='ar' else 'I could not find enough evidence in the uploaded document to answer this. I will not add information from outside the document.'), {'intent':'document_grounded','confidence':0.08,'pipeline':['document_scope','retrieve','abstain']}
            answer=self._synthesize(plan,best)
            # Inline page citations are generated from the actual selected evidence hits.
            # Cite only pages that contributed selected evidence, never every retrieved page.
            selected_norm={normalize(x) for x in best}; pages=[]
            for h in hits:
                page=h.get('metadata',{}).get('page')
                if not page: continue
                if any(normalize(s) in selected_norm for s in self._sentences(h.get('text',''))):
                    if str(page) not in pages: pages.append(str(page))
            if pages:
                answer += ('\n\nالمصدر داخل المستند: ص ' + '، '.join(pages[:5]) if plan.language=='ar' else '\n\nDocument evidence: p. ' + ', '.join(pages[:5]))
            confidence=min(0.97,max(0.35,float(hits[0].get('hybrid_score',0.35))))
            return answer, {'intent':'document_grounded','confidence':round(confidence,2),'pipeline':['document_scope','retrieve','rerank','evidence_synthesis','self_check'],'evidence_count':len(best)}
        if plan.language=='ar':
            canned={
                'greeting':'مرحبًا بك 👋 أنا Yemen AI. أستطيع مساعدتك في الأسئلة، البرمجة، الدراسة وتحليل المعلومات والمعرفة المحلية. ماذا نبدأ؟',
                'identity':'أنا Yemen AI، مساعد ذكي عربي أولًا داخل هذه المنصة. أعتمد على الاستدلال المحلي واسترجاع المعرفة وسياق المحادثة، وأحاول أن أجيب بدقة دون اختلاق معلومات.',
                'thanks':'العفو، أنا حاضر 😊 إذا أردت نكمل فقط اكتب لي ما تحتاجه.',
                'goodbye':'في أمان الله 👋 عندما تحتاجني ستجدني هنا.',
                'capabilities':'أستطيع فهم نية السؤال، البحث في المعرفة المحلية، استخدام سياق المحادثة، الشرح والتلخيص والمقارنة والخطوات والحسابات البسيطة، والمساعدة في البرمجة والدراسة. كما يمكن تحسين معرفتي بإضافة بيانات موثوقة وتقييم الإجابات وتصحيحها.',
            }
            if plan.intent in canned:return canned[plan.intent],{'intent':plan.intent,'confidence':0.99,'pipeline':['understand','respond']}
            if plan.intent=='continue':
                topic=self._history_topic(history)
                if topic:return 'أكيد، نكمل من آخر نقطة وصلنا إليها:\n\n'+topic+'\n\nإذا أردت التوسع أكثر، اكتب: «اشرح أكثر» أو اسأل عن الجزء الذي تريد التركيز عليه.',{'intent':'continue','confidence':0.78,'pipeline':['context','continue']}
                return 'أكيد، أنا جاهز نكمل. فقط اذكر الموضوع أو أرسل السؤال التالي.',{'intent':'continue','confidence':0.55,'pipeline':['clarify']}
        concept=self._concept_answer(message,plan.intent) if plan.language=='ar' else None
        best=self._best_sentences(message,hits,5)
        # Curated concept wins for foundational definitions; retrieval can enrich uncommon questions.
        if concept and plan.intent in {'define','explain','question','summarize','steps','why'}:
            return concept,{'intent':plan.intent,'confidence':0.92,'pipeline':['understand','concept_reasoning','self_check']}
        if not best and concept:return concept,{'intent':plan.intent,'confidence':0.87,'pipeline':['understand','concept_fallback']}
        if best:
            answer=self._synthesize(plan,best)
            confidence=min(0.95,max(0.25,float(hits[0].get('hybrid_score',0)) if hits else 0.25))
            if self._self_check(answer,message,plan.language):
                return answer,{'intent':plan.intent,'confidence':round(confidence,2),'pipeline':['understand','retrieve','rerank','synthesize','self_check'],'evidence_count':len(best)}
        fallback='لا أملك معرفة محلية كافية لأجيب عن هذا السؤال بدقة حتى الآن. يمكنك إضافة مصدر موثوق إلى المنصة أو إعادة صياغة السؤال بشكل أكثر تحديدًا.' if plan.language=='ar' else 'I do not have enough local knowledge to answer that accurately yet. Add reliable training material or make the question more specific.'
        return fallback,{'intent':plan.intent,'confidence':0.12,'pipeline':['understand','retrieve','abstain']}
