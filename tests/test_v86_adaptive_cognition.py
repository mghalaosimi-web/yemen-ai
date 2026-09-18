from backend.services.cognitive_orchestrator import CognitiveOrchestrator
from backend.services.memory_service import MemoryService

def test_reference_resolution_uses_prior_topic():
    c=CognitiveOrchestrator()
    p,_=c.build('اشرح اكثر', [{'role':'user','content':'ما هو الذكاء الاصطناعي؟'}], [], [])
    assert p.context_used and 'الذكاء الاصطناعي' in p.resolved

def test_relevant_memory_not_all_memory():
    c=CognitiveOrchestrator()
    memories=[{'content':'أنا أعمل على مشروع Yemen AI','importance':.8},{'content':'أحب كرة القدم','importance':.9}]
    selected=c.relevant_memories('ساعدني في مشروع Yemen AI',memories)
    assert selected and 'Yemen AI' in selected[0]['content']

def test_plan_has_subgoals():
    c=CognitiveOrchestrator(); p,_=c.build('كيف أبدأ تعلم بايثون؟',[],[],[])
    assert p.mode=='plan' and len(p.subgoals)>=3
