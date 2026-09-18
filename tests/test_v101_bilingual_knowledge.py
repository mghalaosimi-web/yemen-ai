import pytest
from backend.services.bilingual_knowledge_service import BilingualKnowledgeService


def test_bilingual_knowledge_service():
    service = BilingualKnowledgeService()

    # 1. Language detection
    assert service.detect_language("مرحبا") == "ar"
    assert service.detect_language("Hello World") == "en"
    assert service.detect_language("اشرح FastAPI بالعربي") == "mixed"

    # 2. Term linking
    cid = service.link_terms("التوليد المعزز بالاسترجاع", "Retrieval Augmented Generation", "concept_rag")
    assert cid == "concept_rag"

    # 3. Canonical concept resolution
    res_ar = service.resolve_canonical_concept("التوليد المعزز بالاسترجاع")
    res_en = service.resolve_canonical_concept("Retrieval Augmented Generation")
    assert res_ar == "concept_rag"
    assert res_en == "concept_rag"

    # 4. Cross language search
    search_res = service.search_cross_language("Retrieval Augmented Generation")
    assert search_res["language"] in ["en", "mixed"]
    assert len(search_res["concepts"]) >= 1
