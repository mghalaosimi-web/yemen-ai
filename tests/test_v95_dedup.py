"""
tests/test_v95_dedup.py
========================
Tests for knowledge deduplication in the vector store.
"""
import pytest
from pathlib import Path
from backend.rag.store import JsonVectorStore


@pytest.fixture
def store(tmp_path):
    return JsonVectorStore(str(tmp_path / 'test_store.json'))


def test_add_duplicate_text_returns_existing(store):
    item1 = store.add("الفضاء الخارجي يحتوي على ملايين النجوم.", {'source': 'test1'})
    item2 = store.add("الفضاء الخارجي يحتوي على ملايين النجوم.", {'source': 'test2'})
    assert item1['id'] == item2['id'], "duplicate text must return the same item"
    assert len(store.items) == 1


def test_different_texts_are_separate(store):
    store.add("نص المعلومة الأولى.", {'source': 'a'})
    store.add("نص المعلومة الثانية مختلف تماماً.", {'source': 'b'})
    assert len(store.items) == 2


def test_repeated_ingestion_does_not_multiply(store):
    text = "تكرار هذا النص لا يجب أن يضاعف الإدخالات في المخزن."
    for _ in range(5):
        store.add(text, {'source': 'repeat'})
    assert len(store.items) == 1


def test_fingerprint_persists_across_reload(tmp_path):
    path = str(tmp_path / 'persist.json')
    s1 = JsonVectorStore(path)
    s1.add("محتوى يجب أن يكون مستمراً عبر إعادة التحميل.", {'source': 'p'})
    assert len(s1.items) == 1

    s2 = JsonVectorStore(path)
    # Attempt to add same text to the reloaded store
    s2.add("محتوى يجب أن يكون مستمراً عبر إعادة التحميل.", {'source': 'p'})
    assert len(s2.items) == 1, "reloaded store must not duplicate existing content"


def test_whitespace_normalisation_deduplicates(store):
    store.add("  النص   مع  مسافات.  ", {'source': 'a'})
    store.add("النص   مع  مسافات.", {'source': 'b'})
    # Fingerprint is on stripped text, so these should deduplicate
    # (both normalise to same stripped content)
    # Note: our fingerprint is on text.strip() so these two should be the same
    assert len(store.items) == 1


def test_remove_where_updates_fp_index(store):
    store.add("الأولى تبقى.", {'knowledge_id': 1})
    store.add("الثانية تُحذف.", {'knowledge_id': 2})
    assert len(store.items) == 2
    removed = store.remove_where(lambda x: x.get('metadata', {}).get('knowledge_id') == 2)
    assert removed == 1
    assert len(store.items) == 1
    # Re-adding the removed text should succeed (not be treated as duplicate)
    store.add("الثانية تُحذف.", {'knowledge_id': 3})
    assert len(store.items) == 2
