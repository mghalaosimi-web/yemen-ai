from pathlib import Path
from backend.rag.ingest import read_document_pages
from backend.services.local_brain import LocalReasoningEngine

def test_strict_grounded_abstains_without_evidence():
    answer, meta = LocalReasoningEngine().answer('ما هو موضوع غير موجود؟', [], grounded_only=True)
    assert 'لم أجد داخل المستند' in answer
    assert meta['intent'] == 'document_grounded'

def test_strict_grounded_uses_evidence_only():
    hits=[{'text':'يشرح المستند أن الطاقة الشمسية مصدر متجدد للطاقة ويمكن استخدامها لتوليد الكهرباء.', 'score':0.9, 'metadata':{'source':'doc.pdf','page':3}}]
    answer, meta = LocalReasoningEngine().answer('ماذا يقول المستند عن الطاقة الشمسية؟', hits, grounded_only=True)
    assert 'الطاقة الشمسية' in answer
    assert 'ص 3' in answer
    assert meta['intent'] == 'document_grounded'

def test_txt_page_metadata(tmp_path):
    p=tmp_path/'a.txt'; p.write_text('هذه وثيقة اختبار عن اليمن والبحث العلمي.',encoding='utf-8')
    pages=read_document_pages(str(p))
    assert pages and pages[0][0] == 1
    assert pages[0][2]['ocr'] is False
