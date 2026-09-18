from pathlib import Path
from backend.rag.store import JsonVectorStore
from backend.rag.service import RAGService
from backend.training.pipeline import KnowledgeTrainingPipeline

def test_arabic_paraphrase_and_typo_recall(tmp_path):
    rag=RAGService(JsonVectorStore(str(tmp_path/'vectors.json')))
    rag.store.add('لغة بايثون تستخدم في البرمجة وتحليل البيانات والذكاء الاصطناعي.', {'source':'test'})
    assert rag.context('ما استخدامات Python؟', limit=1)[0]['text'].startswith('لغة بايثون')

def test_training_pipeline_generates_retrieval_cards(tmp_path):
    source=tmp_path/'lesson.txt'; source.write_text('المنهج العلمي طريقة منظمة تبدأ بالملاحظة ثم الفرضية والاختبار وتحليل النتائج. يساعد هذا الأسلوب على بناء معرفة قابلة للتحقق.',encoding='utf-8')
    class Fake:
        def __init__(self): self.rag=RAGService(JsonVectorStore(str(tmp_path/'vectors.json')))
        def ingest(self,path,metadata_base=None):
            items=self.rag.ingest(path,metadata_base); return {'chunks':len(items),'items':items}
    result=KnowledgeTrainingPipeline(Fake()).train_file(str(source))
    assert result['training_cards'] >= 1
