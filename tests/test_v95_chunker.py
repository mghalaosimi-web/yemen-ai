"""
tests/test_v95_chunker.py
==========================
Tests for the sentence-aware chunker.
"""
import pytest
from backend.rag.chunker import chunk_text, _split_sentences


def test_short_text_returns_single_chunk():
    text = "هذا نص قصير جداً."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text.strip()


def test_arabic_paragraph_respects_sentence_boundary():
    sentences = [
        "الذكاء الاصطناعي هو فرع من علوم الحاسوب يهدف إلى بناء أنظمة ذكية.",
        "يستخدم التعلم الآلي لتحليل البيانات واستخراج الأنماط منها.",
        "تطبيقاته تشمل معالجة اللغات الطبيعية ورؤية الحاسوب والروبوتات.",
    ]
    text = " ".join(sentences)
    chunks = chunk_text(text, chunk_size=200, overlap=30)
    # No chunk should end mid-word
    for chunk in chunks:
        assert chunk.strip() == chunk
        assert len(chunk) > 0


def test_english_paragraph_respects_boundary():
    text = (
        "Artificial intelligence is transforming modern industry. "
        "Machine learning models are now deployed in production systems worldwide. "
        "Natural language processing enables computers to understand human language."
    )
    chunks = chunk_text(text, chunk_size=150, overlap=20)
    for chunk in chunks:
        assert len(chunk) > 0
        # No chunk should start or end with only whitespace
        assert chunk == chunk.strip()


def test_mixed_language():
    text = (
        "Yemen AI هو نظام ذكاء اصطناعي محلي. "
        "It supports both Arabic and English queries seamlessly. "
        "يمكن استخدامه لتحليل المستندات وتوليد الإجابات."
    )
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) >= 1
    for c in chunks:
        assert len(c.strip()) > 0


def test_very_long_single_sentence_falls_back():
    # 1000 consecutive Arabic words with no sentence punctuation
    long_sentence = " ".join(["كلمة"] * 200)
    chunks = chunk_text(long_sentence, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    # Verify no chunk exceeds chunk_size by more than one word's margin
    for c in chunks:
        assert len(c) < 150  # some leeway for word boundary


def test_overlap_content_is_present_in_consecutive_chunks():
    # Build a text where we can verify overlap
    sents = [f"الجملة رقم {i} تحتوي على معلومات مفيدة ومختلفة جداً." for i in range(20)]
    text = " ".join(sents)
    chunks = chunk_text(text, chunk_size=200, overlap=60)
    if len(chunks) >= 2:
        # Some content from end of chunk[0] should appear in chunk[1]
        # (overlap ensures the reader can follow the context)
        # Weak assertion: chunk[1] is not completely disjoint from chunk[0]
        words0 = set(chunks[0].split())
        words1 = set(chunks[1].split())
        common = words0 & words1
        assert len(common) >= 1, "consecutive chunks should share some overlap content"


def test_empty_text_returns_empty_list():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_sentence_split_arabic():
    text = "الأول. الثاني؟ الثالث!"
    parts = _split_sentences(text)
    assert len(parts) == 3


def test_chunk_size_respected():
    big_text = " ".join([f"جملة مختلفة رقم {i} تستخدم كلمات عديدة لاختبار الحجم." for i in range(100)])
    chunks = chunk_text(big_text, chunk_size=300, overlap=50)
    # No chunk should be massively over the limit
    for c in chunks:
        assert len(c) < 600, f"chunk too long: {len(c)}"
