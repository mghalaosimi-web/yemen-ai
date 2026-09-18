import pytest
from backend.training.personal_context_importer import PersonalContextImporter


def test_personal_context_importer_text():
    importer = PersonalContextImporter()
    
    # 1. Test missing source returns awaiting_source
    res_await = importer.import_context(source_path="non_existent_file.md")
    assert res_await["status"] == "awaiting_source"

    # 2. Test explicit markdown content import
    content = """
# Professional Profile
Role: Lead AI Engineer
Skills: Python, FastAPI, RAG, SQLite

# Working Style
Preferred Language: Arabic
    """
    res = importer.import_context(content=content, source_id="test_master")
    assert res["status"] == "imported"
    assert res["facts_imported"] + res["duplicates_skipped"] >= 2
