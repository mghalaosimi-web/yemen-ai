from backend.services.local_brain import LocalReasoningEngine

def test_arabic_greeting():
    a,m=LocalReasoningEngine().answer('مرحبا')
    assert 'Yemen AI' in a and m['intent']=='greeting'

def test_identity_no_internal_leak():
    a,m=LocalReasoningEngine().answer('من أنت؟')
    assert 'SESSION CONTEXT' not in a and 'أنا Yemen AI' in a

def test_grounded_answer():
    hits=[{'score':0.8,'text':'RAG يعني استرجاع معلومات ذات صلة ثم استخدامها لتكوين إجابة مبنية على مصادر المعرفة المتاحة.','metadata':{'source':'test'}}]
    a,m=LocalReasoningEngine().answer('ما هو RAG؟',hits)
    assert 'RAG' in a and 'SESSION CONTEXT' not in a

def test_typo_and_define_intent():
    b=LocalReasoningEngine()
    assert b.intent('اشرحلي هاذا') == 'explain'
    assert b.intent('ماهو RAG') == 'define'

def test_calculation():
    a,m=LocalReasoningEngine().answer('12*7')
    assert '84' in a and m['intent']=='calculation'

def test_followup_context():
    history=[{'role':'user','content':'اشرح RAG'},{'role':'assistant','content':'RAG يجمع الاسترجاع مع توليد الإجابة اعتمادًا على مصادر معرفة.'}]
    a,m=LocalReasoningEngine().answer('كمل',history=history)
    assert m['intent']=='continue' and 'RAG' in a
