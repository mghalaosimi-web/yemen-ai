from app.services.intelligence_provider import get_intelligence

class AIService:
    @property
    def intelligence(self):
        return get_intelligence()

    def respond(self, message, session_id='default', document_id=None, document_owner=None, user_role='user'):
        result = self.intelligence.chat(
            message,
            session_id=session_id,
            document_id=document_id,
            document_owner=document_owner,
            user_id=document_owner or 'owner',
            user_role=user_role
        )
        return {
            'reply': result.get('answer', 'لم يتم توليد إجابة'),
            'engine': 'Yemen AI Local Intelligence Engine',
            'mode': 'offline_reasoning',
            'status': result.get('status', 'operational'),
            'sources': result.get('sources', []),
            'provider': result.get('provider'),
            'reasoning': result.get('reasoning', {}),
            'retrieval_count': result.get('retrieval_count', 0),
            'session_id': result.get('session_id', session_id)
        }

ai_service = AIService()
