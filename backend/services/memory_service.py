"""
backend/services/memory_service.py
==================================
v9.6 Intelligent Memory & Decay Ranking Layer.

Manages short-term conversation context, long-term user facts, and memory decay.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from app.data.database import save_message, conversation_history, save_memory, recent_memories
from backend.services.local_brain import normalize, tokens


class MemoryService:
    """Intelligent memory management service with relevance recall and decay."""

    def context(self, session_id: str, limit: int = 8) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        history = conversation_history(session_id, limit=limit)
        memories = recent_memories(session_id, limit=16)
        ranked = self.rank_memories(memories)
        return history, ranked

    def calculate_decay(self, created_at_str: str, base_importance: float = 0.5) -> float:
        """Calculate memory decay score based on age."""
        if not created_at_str:
            return base_importance
        try:
            created = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            hours_old = max(0.0, (now - created).total_seconds() / 3600.0)
            # Soft exponential decay with half-life of 72 hours
            decay_factor = 0.5 ** (hours_old / 72.0)
            return round(base_importance * decay_factor, 3)
        except Exception:
            return base_importance

    def rank_memories(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank memories by effective importance considering decay."""
        ranked = []
        for m in memories or []:
            item = dict(m)
            created_at = item.get('created_at', '')
            importance = float(item.get('importance', 0.5) or 0.5)
            item['decay_score'] = self.calculate_decay(created_at, importance)
            ranked.append(item)
        ranked.sort(key=lambda x: (x.get('decay_score', 0), x.get('id', 0)), reverse=True)
        return ranked

    def _stable_fact(self, text: str) -> bool:
        n = normalize(text)
        patterns = ['انا اسمي', 'اسمي ', 'احب ', 'افضل ', 'مشروعي ', 'اعمل على', 'اريد ان', 'هدفي ']
        return any(p in n for p in patterns) and len(tokens(text)) >= 3

    def remember_turn(self, session_id: str, user_message: str, assistant_answer: str):
        save_message(session_id, 'user', user_message)
        save_message(session_id, 'assistant', assistant_answer)
        if self._stable_fact(user_message):
            metadata = {
                'source': 'explicit_statement',
                'type': 'learned_preference',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'confidence': 0.88,
                'importance': 0.85
            }
            save_memory(session_id, 'explicit_user_context', user_message.strip()[:1000], 0.85, metadata)
