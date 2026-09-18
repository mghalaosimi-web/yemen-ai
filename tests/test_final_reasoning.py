from backend.services.reasoning_control import ReasoningControlService

class Graph:
    def related_context(self,q,limit=8):
        return [{'name':'alpha'},{'name':'beta'}]
class Rag:
    def context(self,q,limit=3,min_score=.02,metadata_filter=None):
        return [{'text':f'{q} evidence','metadata':{'source':q},'hybrid_score':.5}]

def test_two_hop_retrieval_and_fusion():
    c=ReasoningControlService(); concepts,hits=c.expand_retrieval('question',Graph(),Rag())
    assert concepts==['alpha','beta'] and len(hits)==2
    fused=c.fuse_hits([{'text':'direct','metadata':{'source':'d'},'hybrid_score':.8}],hits)
    assert fused[0]['reasoning_hop']==1 and any(x['reasoning_hop']==2 for x in fused)

def test_conflict_requires_shared_context():
    c=ReasoningControlService()
    assert not c.conflicts([{'text':'الطقس نعم جميل'},{'text':'البرمجة لا تحتاج ذلك'}])
    assert c.conflicts([{'text':'النظام مسموح للطلاب'},{'text':'النظام غير مسموح للطلاب'}])

def test_abstention_policy():
    c=ReasoningControlService()
    assert c.should_abstain(.1,[{'text':'weak'}],[])
    assert not c.should_abstain(.8,[{'text':'good'}],[])
