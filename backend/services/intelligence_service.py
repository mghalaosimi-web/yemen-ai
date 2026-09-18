import time
from typing import Dict, Any, List, Optional
from backend.ai.factory import get_ai_provider
from backend.rag.service import RAGService
from backend.services.memory_service import MemoryService
from backend.services.local_brain import LocalReasoningEngine
from backend.services.cognitive_orchestrator import CognitiveOrchestrator
from app.data.database import get_setting
from backend.services.knowledge_graph import KnowledgeGraphService
from backend.services.reasoning_control import ReasoningControlService
from backend.services.query_analyzer import QueryAnalyzer
from backend.services.context_resolver import ContextResolver
from backend.services.answer_planner import AnswerPlanner
from backend.services.response_critic import ResponseCritic
from backend.services.language_policy import LanguagePolicy
from backend.services.arabic_normalizer import ArabicNormalizer
from backend.services.semantic_expander import SemanticQueryExpander
from backend.services.task_decomposer import TaskDecomposer
from backend.services.consistency_engine import EvidenceConsistencyAnalyzer
from backend.services.claim_grounding import ClaimGroundingEngine
from backend.services.knowledge_confidence import KnowledgeConfidenceProfile


from backend.services.personal_knowledge_service import PersonalKnowledgeService
from backend.services.bilingual_knowledge_service import BilingualKnowledgeService
from backend.services.concept_mapper import ConceptMapper
from backend.services.terminology_service import TerminologyService
from backend.services.project_memory_service import ProjectMemoryService
from backend.services.user_interaction_profile import UserInteractionProfileService
from backend.services.knowledge_quality_validator import KnowledgeQualityValidator
from backend.services.knowledge_pack_registry import KnowledgePackRegistry
from backend.services.access_control import KnowledgeAccessContext, filter_by_access_scope


class IntelligenceService:
    def __init__(self):
        self.rag = RAGService()
        self.memory = MemoryService()
        self.graph = KnowledgeGraphService()
        self.brain = LocalReasoningEngine()
        self.cognition = CognitiveOrchestrator()
        self.control = ReasoningControlService()
        self.analyzer = QueryAnalyzer()
        self.resolver = ContextResolver()
        self.planner = AnswerPlanner()
        self.critic = ResponseCritic()
        self.language_policy = LanguagePolicy()

        # v10.0 Core Semantic & Reasoning Engines
        self.normalizer = ArabicNormalizer()
        self.expander = SemanticQueryExpander()
        self.decomposer = TaskDecomposer()
        self.consistency_analyzer = EvidenceConsistencyAnalyzer()
        self.grounding_engine = ClaimGroundingEngine()
        self.confidence_profile = KnowledgeConfidenceProfile()

        # v10.1 Personal Knowledge, Bilingual & Project Memory Subsystems
        self.personal_knowledge = PersonalKnowledgeService()
        self.bilingual = BilingualKnowledgeService()
        self.concept_mapper = ConceptMapper()
        self.terminology = TerminologyService()
        self.project_memory = ProjectMemoryService()
        self.user_profile = UserInteractionProfileService()
        self.quality_validator = KnowledgeQualityValidator()
        self.pack_registry = KnowledgePackRegistry()

        # v10.2 Conversation Orchestrator
        from backend.services.conversation_orchestrator import ConversationOrchestrator
        self.orchestrator = ConversationOrchestrator()

        self.provider_config = {}
        self.reload_provider()

    def reload_provider(self, config=None):
        if config is None:
            try:
                config = get_setting('ai_provider_config', {}) or {}
            except Exception:
                config = {}
        self.provider_config = {k: v for k, v in dict(config).items() if k in {'provider', 'model', 'base_url'}}
        self.provider = get_ai_provider(self.provider_config)
        return self.health()

    def chat(self, message: str, session_id='default', document_id=None, document_owner=None, user_id='owner', user_role='admin'):
        return self.orchestrator.process_turn(
            service=self,
            message=message,
            session_id=session_id,
            document_id=document_id,
            document_owner=document_owner,
            user_id=user_id,
            user_role=user_role
        )

    def ingest(self, path: str, metadata_base=None):
        items = self.rag.ingest(path, metadata_base=metadata_base)
        graph_result = self.graph.ingest_text(' '.join(str(x.get('text', '')) for x in items), source_ref=path)
        return {'chunks': len(items), 'items': items, 'graph': graph_result}

    def health(self):
        return {
            'provider': self.provider.status(),
            'provider_config': self.provider_config,
            'knowledge': self.rag.store.stats(),
            'rag': {'enabled': True, 'threshold': 0.03, 'mode': 'hybrid'},
            'memory': {'enabled': True},
            'local_reasoning': {
                'enabled': True,
                'features': [
                    'intent', 'arabic_normalization', 'hybrid_retrieval',
                    'grounded_composition', 'conversation_context', 'adaptive_planning',
                    'reference_resolution', 'relevant_memory', 'conflict_signal',
                    'query_analyzer', 'context_resolver', 'answer_planner',
                    'response_critic', 'language_policy', 'task_decomposer',
                    'semantic_expander', 'consistency_analyzer', 'claim_grounding',
                    'knowledge_confidence', 'personal_knowledge', 'bilingual_service',
                    'concept_mapper', 'project_memory', 'security_access_scopes'
                ]
            },
            'knowledge_graph': self.graph.overview(50)['stats'],
            'reasoning_control': self.control.audit(self)
        }
