import pytest
from backend.services.personal_knowledge_service import PersonalKnowledgeService


def test_conflict_detection_and_resolution():
    service = PersonalKnowledgeService()

    # Add initial fact
    f1 = service.add_fact({
        "subject": "owner",
        "predicate": "primary_location",
        "object": "Sana'a",
        "domain": "identity"
    })

    # Detect conflict when new conflicting fact is supplied
    conflicts = service.detect_conflicts({
        "subject": "owner",
        "predicate": "primary_location",
        "object": "Aden"
    })
    assert len(conflicts) >= 1

    # Adding new fact auto-supersedes old fact
    f2 = service.add_fact({
        "subject": "owner",
        "predicate": "primary_location",
        "object": "Aden",
        "domain": "identity"
    })
    old_f1 = service.get_fact(f1.fact_id)
    assert old_f1.status == "superseded"
    assert old_f1.superseded_by == f2.fact_id
