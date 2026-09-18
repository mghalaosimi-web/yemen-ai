from __future__ import annotations
from abc import ABC, abstractmethod
import os, urllib.request, json

class AIProvider(ABC):
    name = 'unknown'
    @abstractmethod
    def generate(self, prompt: str, system: str = '') -> str: raise NotImplementedError
    def status(self) -> dict: return {'provider': self.name, 'configured': True, 'mode': 'unknown'}

class EchoProvider(AIProvider):
    name='echo'
    def generate(self, prompt: str, system: str = '') -> str:
        return 'Yemen AI (local fallback): ' + prompt
    def status(self): return {'provider':self.name,'configured':True,'mode':'local_fallback','note':'No external AI model is connected'}

class OllamaProvider(AIProvider):
    name='ollama'
    def __init__(self, base_url=None, model=None):
        self.base_url=(base_url or os.getenv('OLLAMA_BASE_URL','http://127.0.0.1:11434')).rstrip('/')
        self.model=model or os.getenv('OLLAMA_MODEL','llama3.2')
    def generate(self,prompt:str,system:str='')->str:
        payload=json.dumps({'model':self.model,'prompt':prompt,'system':system,'stream':False}).encode('utf-8')
        req=urllib.request.Request(self.base_url+'/api/generate',data=payload,headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(req,timeout=120) as r:data=json.loads(r.read().decode('utf-8'))
        answer=data.get('response','').strip()
        if not answer: raise RuntimeError('Ollama returned an empty response')
        return answer
    def status(self): return {'provider':self.name,'configured':bool(self.model),'mode':'local_model','model':self.model,'base_url':self.base_url}

class OpenAICompatibleProvider(AIProvider):
    name='openai-compatible'
    def __init__(self,base_url=None,api_key=None,model=None):
        self.base_url=(base_url or os.getenv('AI_API_BASE_URL','')).rstrip('/')
        self.api_key=api_key or os.getenv('AI_API_KEY','')
        self.model=model or os.getenv('AI_MODEL','')
    def generate(self,prompt:str,system:str='')->str:
        if not self.base_url or not self.model: raise RuntimeError('AI_API_BASE_URL and AI_MODEL are required')
        payload=json.dumps({'model':self.model,'messages':[{'role':'system','content':system or 'You are Yemen AI.'},{'role':'user','content':prompt}],'temperature':0.4}).encode('utf-8')
        headers={'Content-Type':'application/json'}
        if self.api_key: headers['Authorization']='Bearer '+self.api_key
        req=urllib.request.Request(self.base_url+'/v1/chat/completions',data=payload,headers=headers,method='POST')
        with urllib.request.urlopen(req,timeout=120) as r:data=json.loads(r.read().decode('utf-8'))
        answer=data['choices'][0]['message']['content'].strip()
        if not answer: raise RuntimeError('AI provider returned an empty response')
        return answer
    def status(self): return {'provider':self.name,'configured':bool(self.base_url and self.model),'mode':'remote_api','model':self.model,'base_url':self.base_url or None,'api_key_configured':bool(self.api_key)}
