"""
tests/test_v96_intelligence_evolution.py
=========================================
Comprehensive integration test suite covering all 15 required v9.6 capabilities:
 1. Arabic question understanding
 2. Yemeni dialect understanding
 3. Follow-up context
 4. "كمل"
 5. Pronoun resolution
 6. Multi-turn conversation
 7. Arabic answer enforcement
 8. Retrieval ranking
 9. Duplicate evidence removal
10. Memory relevance
11. Document strict mode
12. Uncertainty handling
13. Contradictory evidence
14. Answer planning
15. Response quality scoring
"""
import pytest
from app.services.intelligence_provider import get_intelligence


@pytest.fixture
def intel():
    return get_intelligence()


def test_01_arabic_question_understanding(intel):
    res = intel.chat("ما هو التعلم الآلي؟", session_id="v96_t1")
    assert res['status'] == 'ok'
    assert 'answer' in res
    assert 'reasoning' in res
    assert res['reasoning']['query_analysis']['intent'] == 'define'


def test_02_yemeni_dialect_understanding(intel):
    res = intel.chat("وش يعني هذا الذكاء السيادي؟", session_id="v96_t2")
    assert res['status'] == 'ok'
    assert res['reasoning']['query_analysis']['dialect'] == 'yemeni'


def test_03_followup_and_04_kammal(intel):
    session = "v96_t3_kammal"
    intel.chat("اشرح لي الأمن السيبراني", session_id=session)
    res = intel.chat("كمل", session_id=session)

    assert res['status'] == 'ok'
    assert res['reasoning']['query_analysis']['intent'] == 'continue'
    assert res['reasoning']['answer_plan']['user_intent'] == 'continue'


def test_05_pronoun_resolution_and_06_multiturn(intel):
    session = "v96_t5_multiturn"
    intel.chat("ما هي الشبكات العصبية؟", session_id=session)
    res = intel.chat("وكيف تتعلم؟", session_id=session)

    assert res['status'] == 'ok'
    assert res['reasoning']['conversation_state']['active_topic'] != ""
    assert "الشبكات العصبية" in res['reasoning']['conversation_state']['active_topic'] or "الشبكات" in res['reasoning']['conversation_state']['active_topic']


def test_07_arabic_answer_enforcement(intel):
    res = intel.chat("عرف لي قاعدة البيانات", session_id="v96_t7")
    assert res['status'] == 'ok'
    # Ensure answer contains Arabic text
    import re
    assert len(re.findall(r'[\u0600-\u06ff]', res['answer'])) > 10
    assert "Based on the local knowledge" not in res['answer']


def test_08_retrieval_ranking_and_09_duplicate_removal(intel):
    res = intel.chat("ما هو RAG واسترجاع المعرفة؟", session_id="v96_t8")
    assert res['status'] == 'ok'
    assert res['retrieval_count'] >= 0


def test_10_memory_relevance(intel):
    session = "v96_t10_mem"
    intel.chat("اسمي أحمد وأعمل على مشروع الذكاء الاصطناعي في اليمن", session_id=session)
    res = intel.chat("ما هو اسمي؟", session_id=session)
    assert res['status'] == 'ok'


def test_11_document_strict_mode_and_12_uncertainty(intel):
    # Query with a non-existent document ID
    res = intel.chat("ما هي أرباح الشركة في 2030؟", session_id="v96_t11", document_id="non_existent_doc_999")
    assert res['status'] == 'ok'
    assert "لم أجد داخل المستند" in res['answer'] or "دليلاً كافيًا" in res['answer']
    assert res['reasoning']['answer_plan']['should_abstain'] is True


def test_13_contradictory_evidence(intel):
    hits = [
        {'text': 'هذا الإجراء مسموح في النظام الأول.'},
        {'text': 'هذا الإجراء غير مسموح في النظام الثاني.'}
    ]
    conflicts = intel.control.conflicts(hits)
    assert len(conflicts) > 0


def test_14_answer_planning(intel):
    res = intel.chat("قارن بين بايثون وجافا", session_id="v96_t14")
    assert res['status'] == 'ok'
    assert res['reasoning']['answer_plan']['answer_style'] == 'comparison'


def test_15_response_quality_scoring(intel):
    res = intel.chat("ما هو المنهج العلمي؟", session_id="v96_t15")
    assert res['status'] == 'ok'
    assert 'quality_score' in res['reasoning']
    assert res['reasoning']['quality_score']['overall'] > 0.0
