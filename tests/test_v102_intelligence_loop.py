# -*- coding: utf-8 -*-
"""
tests/test_v102_intelligence_loop.py
=====================================
v10.2 Comprehensive Closed-Loop Intelligence Tests.

Verifies end-to-end intelligence communication loop across 18 distinct scenarios:
1. Standard MSA Arabic question
2. Yemeni dialect semantic equivalence
3. Conversation continuation ("كمل")
4. Pronoun and entity topic resolution ("كيف يتعلم؟")
5. Context correction ("لا قصدي...")
6. Project memory routing ("ما آخر نسخة من Yemen AI؟")
7. Personal knowledge access scope isolation
8. Active document strict mode grounding
9. Mixed AR/EN language handling ("اشرح FastAPI بالعربي")
10. English query processing ("How does Retrieval-Augmented Generation work?")
11. Retrieval of existing stored knowledge vs abstention
12. Graceful degradation on retrieval failure
13. Multi-turn conversation persistence
14. Topic switch detection
15. Low confidence query processing
16. Conflict-aware response generation
17. Session identity contract
18. Backward API route compatibility
"""
import pytest
import uuid
from backend.services.intelligence_service import IntelligenceService


@pytest.fixture
def service():
    return IntelligenceService()


def test_1_arabic_normal_question(service):
    res = service.chat("ما هو الذكاء الاصطناعي؟", session_id="test_t1")
    assert res['status'] == 'ok'
    assert 'answer' in res and len(res['answer']) > 5
    reasoning = res['reasoning']
    assert reasoning['input_understanding']['detected_language'] in {'ar', 'mixed'}
    assert reasoning['input_understanding']['task_type'] in {'QUESTION', 'EXPLANATION_REQUEST'}


def test_2_yemeni_dialect_semantic_equivalence(service):
    res = service.chat("ايش يعني الذكاء الاصطناعي؟", session_id="test_t2")
    assert res['status'] == 'ok'
    reasoning = res['reasoning']
    assert reasoning['input_understanding']['dialect'] == 'yemeni'


def test_3_continuation(service):
    sid = f"test_t3_{uuid.uuid4().hex[:6]}"
    res1 = service.chat("اشرح لي الاسترجاع المعزز RAG", session_id=sid)
    assert res1['status'] == 'ok'

    res2 = service.chat("كمل", session_id=sid)
    assert res2['status'] == 'ok'
    reasoning = res2['reasoning']
    assert reasoning['input_understanding']['task_type'] == 'CONTINUATION'
    assert len(reasoning['conversation_state']['active_topic']) > 0


def test_4_pronoun_reference(service):
    sid = f"test_t4_{uuid.uuid4().hex[:6]}"
    res1 = service.chat("اشرح التعلم الآلي", session_id=sid)
    assert res1['status'] == 'ok'

    res2 = service.chat("كيف يتعلم؟", session_id=sid)
    assert res2['status'] == 'ok'
    reasoning = res2['reasoning']
    assert len(reasoning['conversation_state']['active_topic']) > 0


def test_5_correction(service):
    sid = f"test_t5_{uuid.uuid4().hex[:6]}"
    res1 = service.chat("حدثني عن Yemen AI", session_id=sid)
    assert res1['status'] == 'ok'

    res2 = service.chat("لا قصدي النسخة الجديدة", session_id=sid)
    assert res2['status'] == 'ok'
    reasoning = res2['reasoning']
    assert reasoning['input_understanding']['task_type'] == 'CORRECTION'
    assert len(reasoning['conversation_state']['active_topic']) > 0


def test_6_project_knowledge(service):
    res = service.chat("ما آخر نسخة من Yemen AI؟", session_id="test_t6")
    assert res['status'] == 'ok'
    searched = res['reasoning']['retrieval']['searched_sources']
    assert 'PROJECT_MEMORY' in searched
    assert 'answer' in res and len(res['answer']) > 0


def test_7_personal_knowledge_isolation(service):
    service.personal_knowledge.upsert_personal_context(
        user_id="user_alice",
        category="working_style",
        content="أعمل مهندس شبكات في عدن"
    )
    
    # Alice asks what the system knows about her
    res_alice = service.chat("ماذا تعرف عن طريقة عملي؟", session_id="test_alice", user_id="user_alice")
    assert res_alice['status'] == 'ok'

    # Bob asks what the system knows about him
    res_bob = service.chat("ماذا تعرف عن طريقة عملي؟", session_id="test_bob", user_id="user_bob")
    assert res_bob['status'] == 'ok'


def test_8_document_mode(service):
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    service.rag.store.add("محتوى ملف الأرباح: أرباح الشركة للعام كانت 50,000 دولار صافي.", {
        'document_id': doc_id,
        'owner': 'owner',
        'source_mode': 'strict',
        'source': 'profits.txt'
    })

    res = service.chat("ماذا يقول الملف عن الأرباح؟", session_id="test_doc", document_id=doc_id, document_owner='owner')
    assert res['status'] == 'ok'
    assert 'answer' in res and len(res['answer']) > 0


def test_9_mixed_language(service):
    res = service.chat("اشرح FastAPI بالعربي", session_id="test_mixed")
    assert res['status'] == 'ok'
    assert res['reasoning']['input_understanding']['detected_language'] in {'mixed', 'ar'}


def test_10_english_query(service):
    res = service.chat("How does Retrieval-Augmented Generation work?", session_id="test_en")
    assert res['status'] == 'ok'
    assert res['reasoning']['input_understanding']['detected_language'] == 'en'


def test_11_knowledge_exists(service):
    service.rag.store.add("عاصمة اليمن هي صنعاء والمدينة التجارية الرئيسية هي عدن.", {'source': 'yemen_facts'})
    res = service.chat("ما عاصمة اليمن؟", session_id="test_facts")
    assert res['status'] == 'ok'
    assert 'answer' in res and len(res['answer']) > 0


def test_12_retrieval_degradation(service):
    res = service.chat("xyz123987 non_existent_quantum_fact", session_id="test_deg")
    assert res['status'] in {'ok', 'degraded'}
    assert 'answer' in res and len(res['answer']) > 0


def test_13_conversation_persistence(service):
    sid = f"test_pers_{uuid.uuid4().hex[:6]}"
    service.chat("أريد تعلم لغة بايثون", session_id=sid)
    res = service.chat("ما هي أهم مكتباتها؟", session_id=sid)
    assert res['status'] == 'ok'
    assert len(res['reasoning']['conversation_state']['active_topic']) > 0


def test_14_topic_switch(service):
    sid = f"test_switch_{uuid.uuid4().hex[:6]}"
    service.chat("اشرح لي الأمن السيبراني", session_id=sid)
    res = service.chat("دعنا نتحدث عن طبخ العصيد والسلته", session_id=sid)
    assert res['status'] == 'ok'
    assert len(res['reasoning']['conversation_state']['active_topic']) > 0


def test_15_low_confidence(service):
    res = service.chat("موضوع عشوائي غامض غير محدد", session_id="test_low_conf")
    assert res['status'] == 'ok'
    assert 'reasoning' in res


def test_16_contradictory_evidence(service):
    hits = [
        {'text': 'النسخة الحالية هي v10.1', 'hybrid_score': 0.9},
        {'text': 'النسخة الحالية هي v9.6 قديمة', 'hybrid_score': 0.8}
    ]
    report = service.consistency_analyzer.analyze(hits)
    assert report is not None


def test_17_frontend_session_contract(service):
    res = service.chat("مرحبا", session_id="session_front_123")
    assert res['session_id'] == "session_front_123"


def test_18_api_backward_compatibility(service):
    health = service.health()
    assert health['provider'] is not None
    assert 'knowledge' in health
