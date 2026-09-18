import pytest
from app.services.ai_service import get_intelligence
from backend.training.pipeline import KnowledgeTrainingPipeline


def test_training_pipeline_v2():
    intel = get_intelligence()
    pipeline = KnowledgeTrainingPipeline(intel)

    # Ingest a seed file
    res = pipeline.train_file("knowledge_seed/ai/retrieval_augmented_generation.md")
    assert "training_report" in res
    rep = res["training_report"]
    assert rep["documents_processed"] == 1
    assert rep["status"] == "completed"
