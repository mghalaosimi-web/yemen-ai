from backend.services.local_brain import LocalReasoningEngine

def test_baithon_not_goodbye():
    b=LocalReasoningEngine(); assert b.intent("اشرح بايثون") != "goodbye"

def test_pipeline_and_abstain():
    b=LocalReasoningEngine(); a,m=b.answer("ما هو شيء مجهول جدا xyzq")
    assert "pipeline" in m and m["intent"] in {"define","question"}

def test_reasoning_sentence_synthesis():
    b=LocalReasoningEngine(); hits=[{"score":0.9,"text":"الأمن السيبراني يحمي الأنظمة والبيانات. تستخدم المؤسسات سياسات وحلولًا دفاعية لتقليل المخاطر."}]
    a,m=b.answer("اشرح الأمن السيبراني",hits)
    assert "الأمن السيبراني" in a and "synthesize" in m.get("pipeline",[]) or "concept_reasoning" in m.get("pipeline",[])
