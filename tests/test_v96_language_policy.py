"""
tests/test_v96_language_policy.py
==================================
Tests for v9.6 Arabic Response Enforcement.
"""
import pytest
from backend.services.language_policy import LanguagePolicy


@pytest.fixture
def policy():
    return LanguagePolicy()


def test_enforce_arabic_header_replacement(policy):
    eng_text = "Based on the local knowledge available to me:\n\n• الذكاء الاصطناعي مجال واسع."
    ar_text = policy.enforce_arabic(eng_text, "ما هو الذكاء الاصطناعي؟")

    assert "بحسب المعرفة المحلية المتاحة لي:" in ar_text
    assert "Based on the local knowledge" not in ar_text


def test_format_bullets_in_arabic_styles(policy):
    sents = ["الفرع الأول يعتمد على البيانات.", "الفرع الثاني يركز على الخوارزميات."]

    summary_out = policy.format_bullets_in_arabic(sents, style='summary')
    assert "الخلاصة:" in summary_out
    assert "•" in summary_out

    steps_out = policy.format_bullets_in_arabic(sents, style='steps')
    assert "بشكل مرتب:" in steps_out
    assert "1." in steps_out
    assert "2." in steps_out
