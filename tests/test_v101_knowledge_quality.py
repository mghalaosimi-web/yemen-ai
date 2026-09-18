import pytest
from backend.services.knowledge_quality_validator import KnowledgeQualityValidator


def test_knowledge_quality_validator():
    validator = KnowledgeQualityValidator(policy="reject")

    # 1. Valid item
    v_res = validator.validate_item("This is a high quality chunk of knowledge documentation for Yemen AI v10.1.", metadata={"source": "doc1.txt"})
    assert v_res.valid is True
    assert v_res.score >= 0.8

    # 2. Empty item
    empty_res = validator.validate_item("   ")
    assert empty_res.valid is False
    assert len(empty_res.issues) >= 1
