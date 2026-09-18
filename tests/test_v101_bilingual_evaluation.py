import json
import pytest
from app.services.ai_service import get_intelligence


def test_bilingual_evaluation_dataset():
    intel = get_intelligence()

    with open("tests/data/v101_bilingual_evaluation.json", "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    # Test Arabic retrieval
    for item in eval_data["arabic_examples"]:
        res = intel.chat(item["query"])
        assert res["status"] == "ok"
        assert res["answer"] is not None

    # Test English retrieval
    for item in eval_data["english_examples"]:
        res = intel.chat(item["query"])
        assert res["status"] == "ok"
        assert res["answer"] is not None

    # Test Mixed retrieval
    for item in eval_data["mixed_examples"]:
        res = intel.chat(item["query"])
        assert res["status"] == "ok"
        assert res["answer"] is not None
