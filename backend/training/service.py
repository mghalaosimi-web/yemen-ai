from pathlib import Path
from datetime import datetime, timezone
from app.data.database import create_training_run, update_training_run, list_training_runs, training_stats, get_dataset, add_activity
from backend.services.intelligence_service import IntelligenceService
class TrainingService:
 def __init__(self, intelligence=None):
  # Use the application's live IntelligenceService when supplied. Creating a second
  # instance caused training to update a different in-memory store than chat.
  self.intelligence=intelligence or IntelligenceService()
 def train_dataset(self,dataset_id,actor='trainer'):
  dataset=get_dataset(dataset_id)
  if not dataset: raise ValueError('Dataset not found')
  if not dataset.get('filename'): raise ValueError('Dataset has no uploaded file')
  from app.core.config import UPLOAD_DIR
  path=(UPLOAD_DIR/Path(dataset['filename']).name).resolve()
  if not path.exists() or UPLOAD_DIR.resolve() not in path.parents: raise ValueError('Uploaded file not found')
  run_id=create_training_run(dataset_id,actor,'processing'); started=datetime.now(timezone.utc).isoformat()
  try:
   from backend.training.pipeline import KnowledgeTrainingPipeline
   result=KnowledgeTrainingPipeline(self.intelligence).train_file(str(path), metadata_base={'dataset_id':dataset_id,'source':path.name,'training_artifact':'dataset_chunk'}); chunks=result.get('chunks',0)
   metrics={'chunks':chunks,'source':path.name,'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat(),'mode':'knowledge_training_pipeline','training_cards':result.get('training_cards',0),'concept_count':len(result.get('concepts',[]))}
   update_training_run(run_id,'completed',chunks,'',metrics); add_activity('training','training_completed',f'dataset={dataset_id}; chunks={chunks}')
   return {'run_id':run_id,'dataset_id':dataset_id,'status':'completed',**metrics}
  except Exception as exc:
   update_training_run(run_id,'failed',0,str(exc),{'started_at':started}); add_activity('training','training_failed',str(exc)[:180]); raise
 def status(self): return {'training':training_stats(),'runs':list_training_runs(30),'intelligence':self.intelligence.health()}
