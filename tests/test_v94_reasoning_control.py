from backend.services.reasoning_control import ReasoningControlService

def test_evidence_trace_and_calibration():
    c=ReasoningControlService()
    hits=[{'text':'بايثون لغة برمجة تستخدم في الذكاء الاصطناعي وتحليل البيانات.', 'hybrid_score':0.8, 'metadata':{'source':'manual','page':2}}]
    trace=c.evidence_trace('ما استخدامات بايثون في الذكاء الاصطناعي',hits)
    assert trace and trace[0]['matched_concepts']
    assert c.calibrate(.8,hits,[],len(trace)) >= .4

def test_conflict_signal():
    c=ReasoningControlService()
    hits=[{'text':'هذا الإجراء مسموح في الحالة الأولى.'},{'text':'هذا الإجراء غير مسموح في الحالة الثانية.'}]
    assert c.conflicts(hits)
