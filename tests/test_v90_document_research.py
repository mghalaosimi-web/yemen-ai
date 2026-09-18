import tempfile, os, pytest
from backend.rag.store import JsonVectorStore
from backend.services.document_research import DocumentResearch

@pytest.fixture
def research(tmp_path):
    s = JsonVectorStore(str(tmp_path / 'v90_store.json'))
    for page, text in [
        (1, 'الذكاء الاصطناعي مجال يركز على بناء أنظمة تتعلم من البيانات وتدعم اتخاذ القرار.'),
        (2, 'التعلم الآلي فرع من الذكاء الاصطناعي يستخدم الخوارزميات لاكتشاف الأنماط وتحسين الأداء.'),
        (3, 'تقييم النموذج يتم باستخدام بيانات اختبار مستقلة وقياس الدقة ومؤشرات الأداء.'),
    ]:
        s.add(text, {'document_id': 'd1', 'owner': 'u', 'source': 'book.pdf', 'page': page})
    return DocumentResearch(s)

def test_summary(research): assert len(research.summary('d1', 'u')['summary']) >= 2
def test_key_points(research): assert research.key_points('d1', 'u')['key_points']
def test_search(research): assert research.search(['d1'], 'u', 'ما هو التعلم الآلي')['results']
def test_study_plan(research): assert research.study_plan('d1', 'u', 2)['days'] == 2
def test_quiz(research): assert research.quiz('d1', 'u', 3)['questions']
def test_ownership(research): assert research.summary('d1', 'x') is None
