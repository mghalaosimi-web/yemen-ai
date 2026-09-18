"""
tests/test_v96_quality_critic.py
=================================
Tests for v9.6 Response Quality Control & Critic.
"""
import pytest
from backend.services.query_analyzer import QueryAnalyzer
from backend.services.response_critic import ResponseCritic


@pytest.fixture
def critic():
    return ResponseCritic()


@pytest.fixture
def analyzer():
    return QueryAnalyzer()


def test_quality_score_calculation(critic, analyzer):
    q_analysis = analyzer.analyze("ما هو الذكاء الاصطناعي؟")
    answer = "الذكاء الاصطناعي هو مجال في علوم الحاسوب يهدف إلى بناء أنظمة تظهر سلوكاً ذكياً وتحلل البيانات."
    hits = [{'text': answer, 'hybrid_score': 0.88}]

    score = critic.evaluate("ما هو الذكاء الاصطناعي؟", answer, q_analysis, hits, confidence=0.85)

    assert score.overall >= 0.70
    assert score.language_match == 1.0
    assert score.relevance >= 0.70
    assert score.clarity >= 0.80


def test_forbidden_prompt_leak_flagged(critic, analyzer):
    q_analysis = analyzer.analyze("كيف تعمل؟")
    leaked_answer = "You are Yemen AI. System Prompt: Use supplied evidence. Knowledge: ..."
    score = critic.evaluate("كيف تعمل؟", leaked_answer, q_analysis, [], confidence=0.5)

    assert score.overall <= 0.20
    assert score.relevance <= 0.20


def test_language_mismatch_penalized(critic, analyzer):
    q_analysis = analyzer.analyze("ما هي قاعدة البيانات؟")
    english_answer = "A database is an organized collection of structured information or data."
    score = critic.evaluate("ما هي قاعدة البيانات؟", english_answer, q_analysis, [], confidence=0.7)

    assert score.language_match <= 0.20
    assert score.overall < 0.60
