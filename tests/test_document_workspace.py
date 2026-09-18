from backend.services.document_workspace import DocumentWorkspace
from backend.rag.store import JsonVectorStore

def make_store(tmp_path):
    store=JsonVectorStore(tmp_path/'v.json')
    store.add('الأمن السيبراني يحمي الأنظمة والبيانات من الهجمات.',{'document_id':'a','owner':'u','source':'a.pdf','page':1})
    store.add('تتطلب الحماية إدارة كلمات المرور والتحديثات.',{'document_id':'a','owner':'u','source':'a.pdf','page':2})
    store.add('الأمن السيبراني يعتمد على الوقاية والكشف والاستجابة.',{'document_id':'b','owner':'u','source':'b.pdf','page':3})
    store.add('معلومة خاصة بمستخدم آخر.',{'document_id':'x','owner':'other','source':'x.pdf','page':1})
    return store

def test_workspace_lists_only_owned_documents(tmp_path):
    w=DocumentWorkspace(make_store(tmp_path)); docs=w.list_documents('u')
    assert {x['document_id'] for x in docs}=={'a','b'}

def test_workspace_outline_is_page_aware(tmp_path):
    w=DocumentWorkspace(make_store(tmp_path)); out=w.outline('a','u')
    assert out['pages']==2 and {x['page'] for x in out['outline']}=={1,2}

def test_workspace_compare_is_grounded_and_owner_scoped(tmp_path):
    w=DocumentWorkspace(make_store(tmp_path)); out=w.compare(['a','b'],'u','ما هو الأمن السيبراني؟')
    assert out['grounded_only'] and len(out['documents'])==2
    assert w.compare(['a','x'],'u','الأمن') is None
