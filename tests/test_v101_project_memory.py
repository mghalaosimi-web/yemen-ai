import pytest
from backend.services.project_memory_service import ProjectMemoryService


def test_project_memory_service():
    service = ProjectMemoryService()

    # Set project state
    state = service.set_project_state(
        project_id="yemen_ai",
        name="Yemen AI",
        description="Local-First Offline AI System",
        current_version="10.1",
        architecture="Hybrid RAG + Knowledge Graph",
        metadata={"technologies": ["Python", "FastAPI", "SQLite"]}
    )
    assert state["project_id"] == "yemen_ai"
    assert state["current_version"] == "10.1"

    # Add version
    v_id = service.add_project_version("yemen_ai", "10.1", "Personal Knowledge Foundation Release")
    assert v_id is not None

    # Get history
    hist = service.get_project_history("yemen_ai")
    assert len(hist["versions"]) >= 1
