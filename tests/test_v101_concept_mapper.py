import pytest
from backend.services.concept_mapper import ConceptMapper


def test_concept_mapper_operations():
    mapper = ConceptMapper()

    # 1. Register concept
    res = mapper.register_concept(
        concept_id="concept_ml",
        labels={"ar": ["تعلم الآلة", "التعلم الآلي"], "en": ["Machine Learning"]},
        aliases=["ML"]
    )
    assert res["concept_id"] == "concept_ml"

    # 2. Resolve concept by alias
    by_alias = mapper.resolve_concept("ML")
    assert by_alias is not None
    assert by_alias["concept_id"] == "concept_ml"

    # 3. Add alias
    mapper.add_alias("concept_ml", "MachineLearn")
    res_updated = mapper.resolve_concept("MachineLearn")
    assert res_updated is not None
