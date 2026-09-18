import os
from .provider import EchoProvider, OllamaProvider, OpenAICompatibleProvider

def get_ai_provider(config=None):
    config=config or {}
    provider=str(config.get('provider') or os.getenv('AI_PROVIDER','echo')).lower()
    if provider=='ollama':
        return OllamaProvider(base_url=config.get('base_url') or None, model=config.get('model') or None)
    if provider in {'openai','openai-compatible','api'}:
        return OpenAICompatibleProvider(base_url=config.get('base_url') or None, api_key=os.getenv('AI_API_KEY',''), model=config.get('model') or None)
    return EchoProvider()
