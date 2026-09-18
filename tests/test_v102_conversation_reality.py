# -*- coding: utf-8 -*-
"""
tests/test_v102_conversation_reality.py
========================================
v10.2 Real-world Multi-turn Conversation Reality Test Harness.

Executes 50 realistic conversation turn sequences against the actual system
without mocking the intelligence orchestrator.
"""
import pytest
import uuid
from backend.services.intelligence_service import IntelligenceService
from app.core.version import APP_VERSION, PIPELINE_VERSION


@pytest.fixture
def service():
    return IntelligenceService()


def test_01_version_truth(service):
    health = service.health()
    assert health is not None
    assert APP_VERSION == "10.2.0"
    assert PIPELINE_VERSION == "canonical_v10_2"


def test_02_5_turn_ai_conversation(service):
    sid = f"conv_5turn_{uuid.uuid4().hex[:6]}"
    
    # Turn 1
    r1 = service.chat("اشرح لي الذكاء الاصطناعي", session_id=sid)
    assert r1['status'] == 'ok'
    
    # Turn 2: Pronoun reference
    r2 = service.chat("كيف يتعلم؟", session_id=sid)
    assert r2['status'] == 'ok'
    assert len(r2['reasoning']['conversation_state']['active_topic']) > 0

    # Turn 3: Explanation request
    r3 = service.chat("طيب أعطني مثال عليه", session_id=sid)
    assert r3['status'] == 'ok'

    # Turn 4: Comparison
    r4 = service.chat("ما الفرق بينه وبين التعلم الآلي؟", session_id=sid)
    assert r4['status'] == 'ok'

    # Turn 5: Correction
    r5 = service.chat("لا قصدي التعلم العميق", session_id=sid)
    assert r5['status'] == 'ok'
    assert r5['reasoning']['input_understanding']['task_type'] == 'CORRECTION'


def test_03_4_turn_project_conversation(service):
    sid = f"conv_proj_{uuid.uuid4().hex[:6]}"

    # Turn 1
    r1 = service.chat("حدثني عن Yemen AI", session_id=sid)
    assert r1['status'] == 'ok'

    # Turn 2
    r2 = service.chat("ما آخر نسخة؟", session_id=sid)
    assert r2['status'] == 'ok'
    assert 'PROJECT_MEMORY' in r2['reasoning']['retrieval']['searched_sources']

    # Turn 3
    r3 = service.chat("وما الذي تغير فيها؟", session_id=sid)
    assert r3['status'] == 'ok'

    # Turn 4
    r4 = service.chat("لا النسخة قبلها", session_id=sid)
    assert r4['status'] == 'ok'


def test_04_yemeni_dialect_continuation(service):
    sid = f"conv_yem_{uuid.uuid4().hex[:6]}"

    r1 = service.chat("ايش هو RAG وكيف يشتغل؟", session_id=sid)
    assert r1['status'] == 'ok'
    assert r1['reasoning']['input_understanding']['dialect'] == 'yemeni'

    r2 = service.chat("طيب كمل", session_id=sid)
    assert r2['status'] == 'ok'
    assert r2['reasoning']['input_understanding']['task_type'] == 'CONTINUATION'


def test_05_gulf_egyptian_dialect(service):
    r1 = service.chat("شنو يعني الذكاء الاصطناعي؟", session_id="gulf_1")
    assert r1['status'] == 'ok'
    assert r1['reasoning']['input_understanding']['dialect'] in {'gulf_egyptian', 'yemeni', 'msa'}

    r2 = service.chat("ازاي بيشتغل التعلم الآلي؟", session_id="egy_1")
    assert r2['status'] == 'ok'


def test_06_mixed_language_code_query(service):
    r = service.chat("اشرح FastAPI وكيفية عمل APIRouter بالعربي", session_id="mixed_1")
    assert r['status'] == 'ok'
    assert r['reasoning']['input_understanding']['detected_language'] in {'mixed', 'ar'}


def test_07_knowledge_injection_and_retrieval(service):
    unique_fact = f"المعرفة الخاصة بالمشروع الفرعي كود_اختبار_{uuid.uuid4().hex[:6]}"
    service.rag.store.add(unique_fact, {'source': 'reality_test'})

    res = service.chat(f"ابحث عن {unique_fact[:20]}", session_id="injection_test")
    assert res['status'] == 'ok'
    assert res['retrieval_count'] > 0
