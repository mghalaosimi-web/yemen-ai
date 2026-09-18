from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.routes import require
from backend.training.service import TrainingService
from app.services.intelligence_provider import get_intelligence

router = APIRouter(prefix='/api/training', tags=['training'])


def _training_service() -> TrainingService:
    """Return a TrainingService bound to the canonical singleton."""
    return TrainingService(get_intelligence())


class TrainRequest(BaseModel):
    dataset_id: int


@router.get('/status')
def status(claims=Depends(require('admin', 'developer', 'trainer'))):
    return _training_service().status()


@router.post('/run')
def run(body: TrainRequest, claims=Depends(require('admin', 'developer', 'trainer'))):
    try:
        return _training_service().train_dataset(body.dataset_id, claims.get('sub', 'trainer'))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception:
        raise HTTPException(500, detail='Training failed')
