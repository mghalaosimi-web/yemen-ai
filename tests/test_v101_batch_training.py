import pytest
from app.services.ai_service import get_intelligence
from backend.training.pipeline import KnowledgeTrainingPipeline
from backend.training.batch_training import BatchTrainingManager


def test_batch_training_manager():
    intel = get_intelligence()
    pipeline = KnowledgeTrainingPipeline(intel)
    manager = BatchTrainingManager()

    sources = ["knowledge_seed/ai/retrieval_augmented_generation.md", "knowledge_seed/programming/fastapi_framework.md"]
    job_id = manager.create_batch_job(sources)
    assert job_id.startswith("batch_")

    res = manager.run_batch_job(job_id, sources, pipeline)
    assert res["status"] in ["completed", "partial"]
    assert res["processed_sources"] == 2
