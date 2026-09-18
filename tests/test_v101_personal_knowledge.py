import pytest
from backend.services.personal_knowledge_service import PersonalKnowledgeService


def test_personal_knowledge_crud_and_supersede():
    service = PersonalKnowledgeService()
    
    # 1. Add fact
    fact1 = service.add_fact({
        "subject": "owner",
        "predicate": "primary_role",
        "object": "Lead Architect",
        "domain": "professional_profile",
        "language": "en"
    })
    assert fact1.fact_id is not None
    assert fact1.object == "Lead Architect"
    assert fact1.version == 1

    # 2. Get fact
    fetched = service.get_fact(fact1.fact_id)
    assert fetched is not None
    assert fetched.predicate == "primary_role"

    # 3. Update fact (should auto-increment version)
    updated = service.update_fact(fact1.fact_id, "Principal Systems Architect")
    assert updated is not None
    assert updated.object == "Principal Systems Architect"
    assert updated.version == 2

    # 4. Search facts
    results = service.search_facts("Architect", domain="professional_profile")
    assert len(results) >= 1

    # 5. Profile summary
    summary = service.get_profile_summary()
    assert summary["total_facts"] >= 1
