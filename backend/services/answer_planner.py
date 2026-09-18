from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any
from backend.services.query_analyzer import QueryAnalysis
from backend.services.context_resolver import ResolvedContext

@dataclass
class AnswerPlan:
    user_intent: str
    answer_language: str
    depth: str  # 'shallow', 'medium', 'deep', 'research'
    structure: List[str]
    evidence_ids: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    should_abstain: bool = False
    grounded_mode: bool = False
    answer_style: str = 'direct'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_intent': self.user_intent,
            'answer_language': self.answer_language,
            'depth': self.depth,
            'structure': self.structure,
            'evidence_ids': self.evidence_ids,
            'uncertainties': self.uncertainties,
            'should_abstain': self.should_abstain,
            'grounded_mode': self.grounded_mode,
            'answer_style': self.answer_style,
        }


class AnswerPlanner:
    """Dynamic Answer Planning & Depth Adaptation Engine."""

    STRUCTURE_MAP = {
        'define': ['direct_definition', 'key_aspects', 'context_note'],
        'explain': ['core_concept', 'detailed_breakdown', 'practical_example', 'summary_takeaway'],
        'compare': ['comparison_overview', 'key_differences', 'summary_table_or_points'],
        'steps': ['objective', 'ordered_steps', 'verification_checkpoint'],
        'why': ['direct_reason', 'contributing_factors', 'consequence'],
        'how': ['mechanism_overview', 'step_by_step_process', 'key_requirements'],
        'summarize': ['main_summary', 'key_bullet_points'],
        'verification': ['direct_verdict', 'evidence_explanation', 'clarification'],
        'error_inquiry': ['error_cause', 'resolution_steps', 'preventative_tip'],
        'continue': ['continuation_recap', 'expanded_elaboration', 'next_steps'],
        'document_grounded': ['document_evidence', 'page_citations'],
        'research': ['exec_summary', 'key_findings', 'evidence_synthesis', 'conflicts_or_limitations', 'conclusion']
    }

    def plan(
        self,
        analysis: QueryAnalysis,
        context: ResolvedContext,
        evidence_count: int,
        confidence: float,
        is_document_active: bool = False
    ) -> AnswerPlan:
        intent = analysis.intent
        lang = analysis.detected_language

        # Dynamic Depth assessment
        if analysis.question_type == 'research' or analysis.complexity_score >= 0.85:
            depth = 'research'
        elif analysis.complexity_score > 0.65 or intent in {'explain', 'compare', 'error_inquiry'}:
            depth = 'deep'
        elif analysis.complexity_score < 0.35 or intent in {'greeting', 'thanks', 'identity', 'capabilities'}:
            depth = 'shallow'
        else:
            depth = 'medium'

        # Structure selection
        if is_document_active:
            structure = self.STRUCTURE_MAP['document_grounded']
            grounded = True
        elif depth == 'research':
            structure = self.STRUCTURE_MAP['research']
            grounded = False
        else:
            structure = self.STRUCTURE_MAP.get(intent, ['direct_answer', 'supporting_details'])
            grounded = False

        # Abstention decision
        should_abstain = False
        uncertainties = []
        if analysis.requires_retrieval and evidence_count == 0 and intent not in {'greeting', 'thanks', 'identity', 'capabilities', 'goodbye'}:
            if is_document_active:
                should_abstain = True
                uncertainties.append('no_document_evidence')
            elif confidence < 0.20:
                should_abstain = True
                uncertainties.append('insufficient_local_knowledge')

        return AnswerPlan(
            user_intent=intent,
            answer_language=lang,
            depth=depth,
            structure=structure,
            evidence_ids=[],
            uncertainties=uncertainties,
            should_abstain=should_abstain,
            grounded_mode=grounded,
            answer_style=analysis.required_answer_style
        )
