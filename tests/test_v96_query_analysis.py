"""
tests/test_v96_query_analysis.py
=================================
Tests for v9.6 Arabic-First Intent & Query Analysis Layer.
"""
import pytest
from backend.services.query_analyzer import QueryAnalyzer


@pytest.fixture
def analyzer():
    return QueryAnalyzer()


def test_arabic_msa_intent_definition(analyzer):
    res = analyzer.analyze("ما هو الذكاء الاصطناعي؟")
    assert res.detected_language == 'ar'
    assert res.dialect == 'msa'
    assert res.intent == 'define'
    assert res.required_answer_style == 'definition'
    assert 'الذكاء الاصطناعي' in res.concepts


def test_yemeni_dialect_understanding(analyzer):
    res1 = analyzer.analyze("وش يعني هذا؟")
    assert res1.detected_language == 'ar'
    assert res1.dialect == 'yemeni'
    assert res1.intent in {'define', 'explain'}
    assert 'هذا' in res1.reference_terms

    res2 = analyzer.analyze("ليش حصل كذا؟")
    assert res2.dialect == 'yemeni'
    assert res2.intent == 'why'
    assert res2.required_answer_style == 'causal'

    res3 = analyzer.analyze("كمل الشرح")
    assert res3.dialect == 'yemeni'
    assert res3.intent == 'continue'
    assert res3.requires_memory is True


def test_comparison_intent(analyzer):
    res = analyzer.analyze("قارن بين بايثون وجافا")
    assert res.intent == 'compare'
    assert res.required_answer_style == 'comparison'
    assert res.question_type == 'comparative'


def test_procedural_steps_intent(analyzer):
    res = analyzer.analyze("خطوات تعلم البرمجة من البداية")
    assert res.intent == 'steps'
    assert res.required_answer_style == 'steps'
    assert res.question_type == 'procedural'


def test_verification_intent(analyzer):
    res = analyzer.analyze("هل هذا صحيح؟")
    assert res.intent == 'verification'
    assert res.required_answer_style == 'structured'
    assert res.requires_memory is True


def test_english_query(analyzer):
    res = analyzer.analyze("What is machine learning?")
    assert res.detected_language == 'en'
    assert res.dialect == 'english'
    assert res.intent == 'define'
