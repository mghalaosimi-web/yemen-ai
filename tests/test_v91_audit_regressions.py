from pathlib import Path
from backend.rag.store import JsonVectorStore
from backend.rag.service import RAGService
from backend.services.intelligence_service import IntelligenceService
from backend.training.service import TrainingService

def test_training_service_can_use_live_intelligence(tmp_path):
    intel=IntelligenceService()
    service=TrainingService(intel)
    assert service.intelligence is intel

def test_vector_store_remove_where(tmp_path):
    store=JsonVectorStore(str(tmp_path/'vectors.json'))
    store.add('المعلومة الأولى', {'knowledge_id':1})
    store.add('المعلومة الثانية', {'knowledge_id':2})
    assert store.remove_where(lambda x:x.get('metadata',{}).get('knowledge_id')==1)==1
    assert len(store.items)==1
    assert store.items[0]['metadata']['knowledge_id']==2

def test_training_cards_are_retrievable_from_same_live_engine(tmp_path):
    # This regression protects the original bug: training and chat must share one engine/store.
    store=JsonVectorStore(str(tmp_path/'vectors.json'))
    intel=IntelligenceService()
    intel.rag=RAGService(store)
    source=tmp_path/'knowledge.txt'
    source.write_text('الشبكات العصبية تتكون من طبقات مترابطة تتعلم الأنماط من البيانات عبر تعديل الأوزان.',encoding='utf-8')
    result=intel.ingest(str(source),metadata_base={'source':'audit-test'})
    assert result['chunks']>=1
    hits=intel.rag.context('كيف تتعلم الشبكات العصبية من البيانات؟',limit=3,min_score=0.0)
    assert hits
    assert any('الشبكات العصبية' in h['text'] for h in hits)
