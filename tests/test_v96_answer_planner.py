"""
tests/test_v96_answer_planner.py
=================================
Tests for v9.6 Answer Planning Engine.
"""
import pytest
from backend.services.query_analyzer import QueryAnalyzer
from backend.services.context_resolver import ContextResolver
from backend.services.answer_planner import AnswerPlanner


@pytest.fixture
def planner():
    return AnswerPlanner()


@pytest.fixture
def analyzer():
    return QueryAnalyzer()


@pytest.fixture
def resolver():
    return ContextResolver()


def test_plan_structure_for_definition(planner, analyzer, resolver):
    q_analysis = analyzer.analyze("ما هو RAG؟")
    ctx = resolver.resolve(q_analysis, [])
    plan = planner.plan(q_analysis, ctx, evidence_count=3, confidence=0.8)

    assert plan.user_intent == 'define'
    assert 'direct_definition' in plan.structure
    assert plan.should_abstain is False


def test_plan_structure_for_comparison(planner, analyzer, resolver):
    q_analysis = analyzer.analyze("قارن بين بايثون وجافا")
    ctx = resolver.resolve(q_analysis, [])
    plan = planner.plan(q_analysis, ctx, evidence_count=5, confidence=0.85)

    assert plan.user_intent == 'compare'
    assert 'key_differences' in plan.structure
    assert plan.depth == 'deep'


def test_plan_abstention_in_active_document_mode(planner, analyzer, resolver):
    q_analysis = analyzer.analyze("ما هي ميزانية مشروع 2026؟", active_document="doc_123")
    ctx = resolver.resolve(q_analysis, [], active_document="doc_123")
    plan = planner.plan(q_analysis, ctx, evidence_count=0, confidence=0.0, is_document_active=True)

    assert plan.should_abstain is True
    assert 'no_document_evidence' in plan.uncertainties
    assert plan.grounded_mode is True
