import pytest
from backend.services.intelligence_service import IntelligenceService
from backend.services.arabic_normalizer import ArabicNormalizer
from backend.services.semantic_expander import SemanticQueryExpander
from backend.services.task_decomposer import TaskDecomposer
from backend.services.consistency_engine import EvidenceConsistencyAnalyzer
from backend.services.claim_grounding import ClaimGroundingEngine
from backend.services.knowledge_confidence import KnowledgeConfidenceProfile
from backend.rag.embedding_provider import HashEmbeddingProvider, HybridEmbeddingProvider

@pytest.fixture
def intel_service():
    return IntelligenceService()

def test_arabic_normalizer():
    norm = ArabicNormalizer()
    res = norm.normalize("الذكاء الإصطناعي والتعلم الآلي ١٢٣")
    assert "الذكاء الاصطناعي" in res.normalized_text
    assert "123" in res.normalized_text
    assert len(res.search_tokens) >= 3
    assert len(res.light_stems) >= 1

def test_semantic_query_expander():
    expander = SemanticQueryExpander()
    exp = expander.expand("ايش هو الذكاء الصناعي؟")
    terms = [e.term for e in exp]
    assert "ماذا" in terms or any(e.category == 'dialect' for e in exp)
    assert any(e.category in {'concept', 'english_tech', 'synonym'} for e in exp)

def test_task_decomposer():
    decomposer = TaskDecomposer()
    res_simple = decomposer.decompose("ما هو الحاسوب؟")
    assert res_simple.task_type == "simple_question"

    res_comp = decomposer.decompose("قارن بين الذكاء الاصطناعي والتعلم الآلي واشرح الفرق")
    assert res_comp.task_type == "comparison"
    assert res_comp.subtask_count >= 3

def test_consistency_analyzer():
    analyzer = EvidenceConsistencyAnalyzer()
    hits_conflict = [
        {"text": "عدد الطلاب في المدرسة هو 500 طالب."},
        {"text": "عدد الطلاب في المدرسة هو 900 طالب."}
    ]
    report = analyzer.analyze(hits_conflict)
    assert report.has_conflict is True
    assert report.conflict_type == "numeric"

    hits_clean = [
        {"text": "الذكاء الاصطناعي فرع من علوم الحاسوب."},
        {"text": "يتضمن الذكاء الاصطناعي تعلم الالة والشبكات العصبية."}
    ]
    report_clean = analyzer.analyze(hits_clean)
    assert report_clean.has_conflict is False

def test_claim_grounding_engine():
    grounder = ClaimGroundingEngine()
    hits = [{"id": 1, "text": "الذكاء الاصطناعي هو علم محاكاة العقل البشري."}]
    
    draft = "الذكاء الاصطناعي هو علم محاكاة العقل البشري. هذه حقيقة ثابتة."
    ans, claims, stats = grounder.verify_and_ground(draft, hits)
    assert stats['grounded_claims'] >= 1

def test_claim_grounding_strict_document_mode():
    grounder = ClaimGroundingEngine()
    # No matching document hits
    ans, claims, stats = grounder.verify_and_ground("معلومات غير موجودة", [], is_document_active=True, active_document_id="doc123")
    assert ans == ClaimGroundingEngine.ABSTAIN_DOCUMENT_MSG
    assert stats['abstained'] is True

def test_knowledge_confidence_profile():
    profile = KnowledgeConfidenceProfile()
    conf = profile.compute(0.85, [{"text": "d1"}, {"text": "d2"}], has_conflict=False)
    assert conf >= 0.60

def test_pluggable_embedding_fallback():
    hash_p = HashEmbeddingProvider()
    vec = hash_p.embed("اختبار نظام Yemen AI v10")
    assert len(vec) == 768
    assert hash_p.available() is True

def test_chat_semantic_evolution_integration(intel_service):
    res = intel_service.chat("ما هو الذكاء الاصطناعي وكيف يتعلم؟")
    assert res['status'] == 'ok'
    assert 'answer' in res
    reasoning = res['reasoning']
    assert 'task_decomposition' in reasoning
    assert 'arabic_normalization' in reasoning
    assert 'performance' in reasoning
    assert reasoning['performance']['total_ms'] >= 0

def test_chat_yemeni_dialect(intel_service):
    res = intel_service.chat("ايش تقدر تسوي؟")
    assert res['status'] == 'ok'
    assert 'answer' in res

def test_health_diagnostics(intel_service):
    h = intel_service.health()
    assert h['local_reasoning']['enabled'] is True
    assert 'task_decomposer' in h['local_reasoning']['features']
