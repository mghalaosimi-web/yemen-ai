"""
backend/services/context_resolver.py
====================================
v10.2 Context & Reference Resolution Engine.

Maintains multi-turn ConversationState, performs pronoun resolution,
subject inheritance, continuation tracking, correction handling,
and reference binding with dynamic session_id support.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from backend.services.local_brain import normalize, tokens
from backend.services.query_analyzer import QueryAnalysis


@dataclass
class ConversationState:
    session_id: str = 'default'
    active_topic: str = ''
    active_project: str = 'yemen_ai'
    active_entities: List[str] = field(default_factory=list)
    active_document: Optional[str] = None
    last_question: str = ''
    last_answer_summary: str = ''
    unresolved_points: List[str] = field(default_factory=list)
    conversation_goal: str = 'general_assistance'
    answer_depth: str = 'medium'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'active_topic': self.active_topic,
            'active_project': self.active_project,
            'active_entities': self.active_entities,
            'active_document': self.active_document,
            'last_question': self.last_question,
            'last_answer_summary': self.last_answer_summary,
            'unresolved_points': self.unresolved_points,
            'conversation_goal': self.conversation_goal,
            'answer_depth': self.answer_depth,
        }


@dataclass
class ResolvedContext:
    original_query: str
    resolved_query: str
    active_topic: str
    action: str                        # 'NEW_TOPIC', 'CONTINUE', 'REFERENCE', 'CORRECTION', 'CLARIFICATION', 'FOLLOW_UP', 'REPEAT', 'SUMMARIZE', 'COMPARE', 'DEEPEN'
    reference_resolved: bool
    continuation: bool
    conversation_state: ConversationState

    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_query': self.original_query,
            'resolved_query': self.resolved_query,
            'active_topic': self.active_topic,
            'action': self.action,
            'reference_resolved': self.reference_resolved,
            'continuation': self.continuation,
            'conversation_state': self.conversation_state.to_dict(),
        }


class ContextResolver:
    """Multi-turn context and pronoun reference resolver."""

    PRONOUN_VERBS = [
        ('يتعلم', 'كيف يتعلم'),
        ('يعمل', 'كيف يعمل'),
        ('يستفيد', 'كيف يستفيد'),
        ('يستخدم', 'كيف يستخدم'),
        ('يؤثر', 'كيف تؤثر'),
    ]

    def _extract_main_subject(self, text: Any) -> str:
        """Extract primary subject phrase from a question."""
        if not isinstance(text, str):
            text = getattr(text, 'original_text', getattr(text, 'original_query', str(text)))
        if 'inputunderstandingresult' in text.lower():
            m_orig = re.search(r"original_text=['\"]([^'\"]+)['\"]", text)
            if m_orig:
                text = m_orig.group(1)
        norm = normalize(text)
        m = re.search(r'(?:ما هو|ماهو|ما هي|ماهي|تعريف|عن|اشرح|حول|حدثني عن)\s+([\w\s]{3,40})', norm)
        if m:
            subj = m.group(1).strip()
            subj = re.split(r'\b(في|من|على|مع|لتكون|وكيف|ليش|ما)\b', subj)[0].strip()
            if len(subj) >= 3:
                return subj
        ts = tokens(text)
        if ts:
            return ' '.join(ts[:4])
        return text[:60]

    def build_state(self, session_id: str, history: List[Dict[str, Any]], active_document: str | None = None) -> ConversationState:
        state = ConversationState(session_id=session_id, active_document=active_document)
        if not history:
            return state

        last_user = ''
        last_assistant = ''

        for item in reversed(history):
            role = item.get('role')
            content = item.get('content', '').strip()
            if role == 'user' and not last_user and len(content) > 2:
                last_user = content
            elif role == 'assistant' and not last_assistant and len(content) > 10:
                last_assistant = content

            if last_user and last_assistant:
                break

        state.last_question = last_user
        state.last_answer_summary = last_assistant[:250] if last_assistant else ''

        for item in reversed(history[-6:]):
            if item.get('role') == 'user':
                subj = self._extract_main_subject(item.get('content', ''))
                if subj and len(subj) >= 3 and subj not in {'كمل', 'تابع', 'استمر', 'وضح اكثر', 'ما فهمت', 'لا قصدي'}:
                    state.active_topic = subj
                    break

        if not state.active_topic and last_user:
            state.active_topic = self._extract_main_subject(last_user)

        return state

    def resolve(self, query_analysis: Any, history: List[Dict[str, Any]], active_document: str | None = None, session_id: str = 'default') -> ResolvedContext:
        if isinstance(query_analysis, str):
            query = query_analysis
        else:
            query = getattr(query_analysis, 'original_text', getattr(query_analysis, 'original_query', str(query_analysis)))
        norm = getattr(query_analysis, 'normalized_text', getattr(query_analysis, 'normalized_query', normalize(query)))
        task_type = getattr(query_analysis, 'task_type', 'QUESTION')
        intent = getattr(query_analysis, 'intent', 'question')
        ref_terms = getattr(query_analysis, 'reference_terms', [])

        # DYNAMIC BINDING of session_id (Bug fix!)
        state = self.build_state(session_id=session_id, history=history, active_document=active_document)

        resolved_query = query
        ref_resolved = False
        is_continuation = False
        action = 'NEW_TOPIC'

        # 1. Corrections ("لا قصدي...", "لا المعذرة قصدي...")
        if task_type == 'CORRECTION' or any(x in norm for x in ['لا قصدي', 'قصدي', 'بل قصدي', 'لا المعذرة']):
            action = 'CORRECTION'
            # Extract new intended topic
            m = re.search(r'(?:لا قصدي|قصدي|بل قصدي|أقصد)\s+(.*)', query)
            new_target = m.group(1).strip() if m else query
            if state.active_topic:
                resolved_query = f"تعديل وتصحيح الموضوع من '{state.active_topic}' إلى: {new_target}"
                state.active_topic = new_target
                ref_resolved = True
            else:
                resolved_query = f"التصحيح المقصود: {new_target}"
                state.active_topic = new_target

        # 2. Continuation requests ("كمل", "تابع", "استمر", "وضح اكثر")
        elif intent == 'continue' or task_type == 'CONTINUATION' or norm in {'كمل', 'تابع', 'واصل', 'استمر', 'اكمل', 'شرح لي من البدايه', 'وضح اكثر', 'فصل اكثر'}:
            action = 'CONTINUE'
            is_continuation = True
            if state.active_topic:
                resolved_query = f"تابع الشرح والتفصيل بخصوص الموضوع السابق: {state.active_topic}"
                ref_resolved = True
            elif state.last_question:
                resolved_query = f"تابع الشرح والإجابة بخصوص السؤال السابق: {state.last_question}"
                ref_resolved = True

        # 3. Project previous version reference ("النسخة السابقة", "النسخة القديمة")
        elif 'النسخة السابقة' in norm or 'الاصدار السابق' in norm or 'نسخة سابقة' in norm:
            action = 'COMPARE'
            resolved_query = f"{query} | مقارنة بين الإصدار الحالي اليمن أي اي v10.1 والإصدار السابق v9.6"
            ref_resolved = True

        # 4. Referential pronouns ("هذا", "ذلك", "ايش قصده", "وش يعني هذا")
        elif ref_terms or any(x in norm for x in ['هذا', 'هذه', 'ذلك', 'تلك', 'قصده', 'معناه']):
            action = 'REFERENCE'
            if state.active_topic and len(tokens(query)) <= 6:
                if any(x in norm for x in ['معنى', 'قصده', 'يعني']):
                    resolved_query = f"ما معنى وتوضيح {query} بخصوص: {state.active_topic}"
                else:
                    resolved_query = f"{query} بخصوص {state.active_topic}"
                ref_resolved = True

        # 5. Short implicit follow-ups ("كيف يتعلم؟", "وهل يحتاج بيانات كثيرة؟")
        elif state.active_topic and len(tokens(query)) <= 6 and intent in {'how', 'why', 'verification', 'question'}:
            action = 'FOLLOW_UP'
            topic_tokens = set(tokens(state.active_topic))
            query_tokens = set(tokens(query))
            if not (topic_tokens & query_tokens):
                resolved_query = f"{query} بخصوص {state.active_topic}"
                ref_resolved = True
        else:
            # Update state with new topic if query is explicit
            new_subj = self._extract_main_subject(query)
            if new_subj and len(new_subj) >= 3:
                state.active_topic = new_subj

        return ResolvedContext(
            original_query=query,
            resolved_query=resolved_query,
            active_topic=state.active_topic,
            action=action,
            reference_resolved=ref_resolved,
            continuation=is_continuation,
            conversation_state=state
        )
