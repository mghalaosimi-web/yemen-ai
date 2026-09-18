from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.api.routes import require
from app.data.database import set_setting, get_setting, add_activity, add_system_event
from app.services.intelligence_provider import get_intelligence

router = APIRouter(prefix='/api/models', tags=['model-control'])


class ProviderConfig(BaseModel):
    provider: str = Field(pattern='^(echo|ollama|openai-compatible)$')
    model: str = Field(default='', max_length=200)
    base_url: str = Field(default='', max_length=500)


@router.get('/config')
def config(claims=Depends(require('admin', 'developer'))):
    return {'config': get_setting('ai_provider_config', {}), 'runtime': get_intelligence().health()}


@router.put('/config')
def update_config(body: ProviderConfig, claims=Depends(require('admin'))):
    data = body.model_dump()
    if body.provider == 'ollama' and not data['model']:
        data['model'] = 'llama3.2'
    if body.provider == 'ollama' and not data['base_url']:
        data['base_url'] = 'http://127.0.0.1:11434'
    if body.provider == 'openai-compatible' and (not data['model'] or not data['base_url']):
        raise HTTPException(400, 'model and base_url are required for openai-compatible provider')
    set_setting('ai_provider_config', data)
    runtime = get_intelligence().reload_provider(data)
    add_activity(claims['role'], 'ai_provider_updated', body.provider)
    add_system_event('info', 'ai_provider_updated', body.provider)
    return {'message': 'AI provider configuration applied', 'config': data, 'runtime': runtime}


@router.post('/reload')
def reload_runtime(claims=Depends(require('admin', 'developer'))):
    runtime = get_intelligence().reload_provider()
    return {'message': 'AI runtime reloaded', 'runtime': runtime}
