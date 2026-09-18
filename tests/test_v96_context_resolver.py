"""
tests/test_v96_context_resolver.py
===================================
Tests for v9.6 Context & Reference Resolution Engine.
"""
import pytest
from backend.services.query_analyzer import QueryAnalyzer
from backend.services.context_resolver import ContextResolver


@pytest.fixture
def resolver():
    return ContextResolver()


@pytest.fixture
def analyzer():
    return QueryAnalyzer()


def test_pronoun_and_subject_continuation(resolver, analyzer):
    history = [
        {'role': 'user', 'content': 'اشرح لي الذكاء الاصطناعي'},
        {'role': 'assistant', 'content': 'الذكاء الاصطناعي هو مجال في علوم الحاسوب يهدف لبناء أنظمة ذكية...'}
    ]

    # Follow-up: "كيف يتعلم؟"
    q_analysis = analyzer.analyze("كيف يتعلم؟")
    resolved = resolver.resolve(q_analysis, history)

    assert resolved.reference_resolved is True
    assert "الذكاء الاصطناعي" in resolved.resolved_query
    assert resolved.active_topic != ""


def test_continuation_intent_resolution(resolver, analyzer):
    history = [
        {'role': 'user', 'content': 'ما هي خوارزميات البحث؟'},
        {'role': 'assistant', 'content': 'خوارزميات البحث هي طرق منظمة لإيجاد الحلول...'}
    ]

    q_analysis = analyzer.analyze("كمل")
    resolved = resolver.resolve(q_analysis, history)

    assert resolved.continuation is True
    assert resolved.reference_resolved is True
    assert "خوارزميات البحث" in resolved.resolved_query or "سؤال" in resolved.resolved_query


def test_referential_demonstrative_resolution(resolver, analyzer):
    history = [
        {'role': 'user', 'content': 'ما هو الأمن السيبراني؟'},
        {'role': 'assistant', 'content': 'الأمن السيبراني هو حماية الأنظمة والشبكات...'}
    ]

    q_analysis = analyzer.analyze("ايش قصده هذا؟")
    resolved = resolver.resolve(q_analysis, history)

    assert resolved.reference_resolved is True
    assert "الامن السيبراني" in resolved.resolved_query or "السيبراني" in resolved.resolved_query
