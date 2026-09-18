from fastapi import APIRouter,HTTPException,UploadFile,File,Form,Header,Response,Cookie,Request,Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,Field
from pathlib import Path
from datetime import datetime,timezone
import uuid,csv,io
from app.core.config import UPLOAD_DIR,MAX_UPLOAD_MB,APP_VERSION,MAX_MESSAGE_CHARS,ALLOWED_UPLOAD_EXTENSIONS,TOKEN_TTL_MINUTES,COOKIE_SECURE
from app.data.database import *
from app.services.ai_service import ai_service
from app.services.auth_service import verify_password,create_token,decode_token,hash_password
from app.services.seed_importer import import_seed_knowledge, seed_status
from app.services.rate_limiter import limiter as _login_limiter
from backend.services.document_workspace import DocumentWorkspace
from backend.services.document_research import DocumentResearch
from backend.api.knowledge_v101 import router as v101_router

router=APIRouter(prefix='/api',tags=['Yemen AI'])
router.include_router(v101_router)
class Login(BaseModel): username:str=Field(min_length=1,max_length=64); password:str=Field(min_length=1,max_length=256)
class Chat(BaseModel):
    message:str=Field(min_length=1,max_length=MAX_MESSAGE_CHARS)
    session_id:str=Field(default='default',max_length=128)
    document_id:str|None=Field(default=None,max_length=128)
class ChatFeedback(BaseModel):
    message:str=Field(min_length=1,max_length=MAX_MESSAGE_CHARS)
    answer:str=Field(min_length=1,max_length=20000)
    rating:int=Field(ge=1,le=5)
    notes:str=Field(default='',max_length=5000)
    session_id:str=Field(default='default',max_length=128)
class Knowledge(BaseModel): title:str=Field(min_length=2,max_length=200); content:str=Field(min_length=2,max_length=200000); source:str=Field(default='manual',max_length=500)
class UserCreate(BaseModel): username:str=Field(min_length=3,max_length=64,pattern=r'^[A-Za-z0-9_.-]+$'); password:str=Field(min_length=8,max_length=256); role:str=Field(default='user')
class RoleUpdate(BaseModel): role:str
class SettingUpdate(BaseModel): value:object
VALID_ROLES={'admin','developer','trainer','user'}
def get_claims(authorization:str|None=Header(default=None),yemen_ai_token:str|None=Cookie(default=None)):
    token=None
    if authorization:
        if not authorization.startswith('Bearer '): raise HTTPException(401,'Invalid authorization header')
        token=authorization[7:]
    else: token=yemen_ai_token
    if not token: raise HTTPException(401,'Authentication required')
    return decode_token(token)
def require(*roles):
    def checker(claims=Depends(get_claims)):
        if claims.get('role') not in roles: raise HTTPException(403,'Insufficient permission')
        return claims
    return checker
from app.core.version import get_runtime_identity, PIPELINE_VERSION, BUILD_ID
@router.get('/health')
def health():
    identity = get_runtime_identity()
    return {
        'status': 'ok',
        'project': 'Yemen AI',
        'version': APP_VERSION,
        'pipeline_version': PIPELINE_VERSION,
        'build_id': BUILD_ID,
        'started_at': identity['started_at'],
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

@router.get('/admin/runtime')
def admin_runtime(claims=Depends(require('admin', 'developer'))):
    return get_runtime_identity()
@router.post('/auth/login')
def login(payload:Login,response:Response,request:Request):
    ip=request.headers.get('X-Forwarded-For','').split(',')[0].strip() or request.client.host or 'unknown'
    # Rate-limit check BEFORE any credential verification to prevent username enumeration via timing.
    status=_login_limiter.check(ip)
    if not status['allowed']:
        add_system_event('warning','login_rate_limited',f'ip={ip} retry_after={status["retry_after"]}s')
        raise HTTPException(429,detail=f'Too many login attempts. Please wait {status["retry_after"]} seconds before trying again.')
    u=get_user(payload.username)
    if not u or not verify_password(payload.password,u['password_hash']):
        newly_locked=_login_limiter.record_failure(ip)
        if newly_locked:
            add_system_event('warning','login_lockout_triggered',f'ip={ip}')
            add_activity('security','login_lockout',f'ip={ip}')
        raise HTTPException(401,'Invalid credentials')
    _login_limiter.record_success(ip)
    add_activity(u['role'],'login',u['username']); token=create_token(u['username'],u['role'])
    response.set_cookie('yemen_ai_token',token,httponly=True,samesite='lax',secure=COOKIE_SECURE,max_age=TOKEN_TTL_MINUTES*60)
    return {'access_token':token,'token_type':'bearer','user':{'username':u['username'],'role':u['role']}}
@router.post('/auth/logout')
def logout(response:Response):response.delete_cookie('yemen_ai_token');return {'message':'Logged out'}
@router.get('/auth/me')
def me(claims=Depends(get_claims)):return {'username':claims['sub'],'role':claims['role']}
@router.get('/dashboard')
def dashboard(claims=Depends(require('admin','developer'))):return {'stats':stats(),'recent':list_activities(10),'version':APP_VERSION}
@router.get('/datasets')
def datasets(claims=Depends(require('admin','developer','trainer'))):return list_datasets()
@router.delete('/datasets/{dataset_id}')
def remove_dataset(dataset_id:int,claims=Depends(require('admin','developer','trainer'))):
    if not delete_dataset(dataset_id): raise HTTPException(404,'Dataset not found')
    add_activity(claims['role'],'dataset_deleted',str(dataset_id)); return {'message':'Dataset deleted'}
@router.post('/datasets')
def add_dataset(name:str,description:str='',claims=Depends(require('admin','developer','trainer'))):
    if not name.strip():raise HTTPException(400,'name is required')
    i=create_dataset(name.strip(),description);add_activity(claims['role'],'dataset_created',name);return {'id':i,'message':'Dataset created successfully'}
@router.post('/datasets/upload')
async def upload_dataset(name:str=Form(...),description:str=Form(''),file:UploadFile=File(...),claims=Depends(require('admin','developer','trainer'))):
    safe=Path(file.filename or '').name; ext=Path(safe).suffix.lower()
    if not safe or ext not in ALLOWED_UPLOAD_EXTENSIONS:raise HTTPException(400,'Unsupported file type')
    target=UPLOAD_DIR/f'{uuid.uuid4().hex}_{safe}'; size=0
    try:
      with target.open('xb') as f:
       while chunk:=await file.read(1024*1024):
        size+=len(chunk)
        if size>MAX_UPLOAD_MB*1024*1024:raise HTTPException(413,'file too large')
        f.write(chunk)
    except Exception:
      target.unlink(missing_ok=True);raise
    i=create_dataset(name.strip(),description,target.name);add_activity(claims['role'],'dataset_uploaded',safe)
    return {'id':i,'filename':target.name,'message':'File uploaded successfully','ingestion_supported':ext in {'.txt','.md','.csv','.json'}}

@router.post('/datasets/{dataset_id}/ingest')
def ingest_dataset(dataset_id:int,claims=Depends(require('admin','developer','trainer'))):
    with connect() as c:
        row=c.execute('SELECT * FROM datasets WHERE id=?',(dataset_id,)).fetchone()
    if not row: raise HTTPException(404,'Dataset not found')
    filename=row['filename']
    if not filename: raise HTTPException(400,'Dataset has no uploaded file')
    path=(UPLOAD_DIR/Path(filename).name).resolve()
    if not path.exists() or UPLOAD_DIR.resolve() not in path.parents: raise HTTPException(404,'Uploaded file not found')
    job=create_ingestion_job(dataset_id,path.name)
    try:
        result=ai_service.intelligence.ingest(str(path), metadata_base={'dataset_id':dataset_id,'source':path.name,'training_artifact':'dataset_chunk'})
        complete_ingestion_job(job,result['chunks']);add_activity(claims['role'],'dataset_ingested',path.name)
        return {'dataset_id':dataset_id,'job_id':job,'status':'completed',**result}
    except ValueError as e:
        fail_ingestion_job(job,str(e));raise HTTPException(400,str(e))
    except Exception as e:
        fail_ingestion_job(job,str(e));raise HTTPException(500,'Ingestion failed')
@router.get('/ingestion/jobs')
def ingestion_jobs(claims=Depends(require('admin','developer','trainer'))):return list_ingestion_jobs()

@router.get('/activities')
def activities(claims=Depends(require('admin','developer'))):return list_activities()
@router.get('/knowledge')
def knowledge(claims=Depends(require('admin','developer','trainer'))):return list_knowledge()
@router.delete('/knowledge/{knowledge_id}')
def knowledge_delete(knowledge_id:int,claims=Depends(require('admin','developer','trainer'))):
    if not delete_knowledge(knowledge_id): raise HTTPException(404,'Knowledge item not found')
    store=ai_service.intelligence.rag.store
    # Remove original chunks (indexed directly by knowledge_id).
    removed_primary=store.remove_where(lambda x: x.get('metadata',{}).get('knowledge_id')==knowledge_id)
    # Remove derived artifacts (QA cards, concept_index) stamped with source_knowledge_id.
    removed_derived=store.remove_where(lambda x: x.get('metadata',{}).get('source_knowledge_id')==knowledge_id)
    add_activity(claims['role'],'knowledge_deleted',f'id={knowledge_id} primary={removed_primary} derived={removed_derived}')
    return {'message':'Knowledge deleted','removed_primary':removed_primary,'removed_derived':removed_derived}
@router.post('/knowledge')
def knowledge_add(payload:Knowledge,claims=Depends(require('admin','developer','trainer'))):
    i=add_knowledge(payload.title,payload.content,payload.source)
    # Manual knowledge must be immediately searchable; previously it was stored only in SQLite.
    ai_service.intelligence.rag.store.add(payload.content,{'source':payload.source,'knowledge_id':i,'title':payload.title,'training_artifact':'manual_knowledge'})
    add_activity(claims['role'],'knowledge_added',payload.title)
    return {'id':i,'message':'Knowledge added and indexed','indexed':True}
@router.post('/chat/documents')
async def upload_chat_document(file:UploadFile=File(...),claims=Depends(get_claims)):
    safe=Path(file.filename or '').name; ext=Path(safe).suffix.lower()
    if ext not in {'.pdf','.docx','.txt','.md'}: raise HTTPException(400,'يدعم المساعد PDF وDOCX وTXT وMD فقط')
    doc_id=uuid.uuid4().hex
    target=UPLOAD_DIR/f'chat_{claims["sub"]}_{doc_id}_{safe}'; size=0
    try:
        with target.open('xb') as f:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>MAX_UPLOAD_MB*1024*1024: raise HTTPException(413,'الملف كبير جدًا')
                f.write(chunk)
        result=ai_service.intelligence.ingest(str(target),metadata_base={'source':safe,'document_id':doc_id,'owner':claims['sub'],'source_mode':'strict'})
        if not result['chunks']: raise HTTPException(400,'لم يتم استخراج محتوى قابل للاستخدام من الملف')
        add_activity(claims['role'],'chat_document_uploaded',safe)
        return {'document_id':doc_id,'filename':safe,'chunks':result['chunks'],'strict_source':True,'pages':len(sorted({x.get('metadata',{}).get('page') for x in result.get('items',[]) if x.get('metadata',{}).get('page')})),'ocr_pages':len({x.get('metadata',{}).get('page') for x in result.get('items',[]) if x.get('metadata',{}).get('ocr')}),'message':'تمت قراءة المستند وبناء فهرس صفحات. الإجابات التالية ستلتزم بهذا المستند كمصدر.'}
    except HTTPException:
        ai_service.intelligence.rag.store.remove_where(lambda x:x.get('metadata',{}).get('document_id')==doc_id); target.unlink(missing_ok=True); raise
    except Exception as e:
        ai_service.intelligence.rag.store.remove_where(lambda x:x.get('metadata',{}).get('document_id')==doc_id); target.unlink(missing_ok=True); raise HTTPException(400,str(e))

@router.get('/chat/documents/{document_id}')
def chat_document_info(document_id:str,claims=Depends(get_claims)):
    items=[x for x in ai_service.intelligence.rag.store.items if x.get('metadata',{}).get('document_id')==document_id and x.get('metadata',{}).get('owner')==claims['sub']]
    if not items: raise HTTPException(404,'المستند غير موجود أو لا تملك صلاحية الوصول إليه')
    meta=items[0].get('metadata',{})
    pages=sorted({x.get('metadata',{}).get('page') for x in items if x.get('metadata',{}).get('page')})
    ocr_pages=sorted({x.get('metadata',{}).get('page') for x in items if x.get('metadata',{}).get('ocr')})
    return {'document_id':document_id,'filename':meta.get('source'),'chunks':len(items),'pages':len(pages),'page_numbers':pages,'ocr_pages':ocr_pages,'strict_source':True}

@router.delete('/chat/documents/{document_id}')
def remove_chat_document(document_id:str,claims=Depends(get_claims)):
    removed=ai_service.intelligence.rag.store.remove_where(lambda x:x.get('metadata',{}).get('document_id')==document_id and x.get('metadata',{}).get('owner')==claims['sub'])
    return {'removed':removed}

@router.get('/chat/documents')
def list_chat_documents(claims=Depends(get_claims)):
    workspace=DocumentWorkspace(ai_service.intelligence.rag.store)
    return {'documents':workspace.list_documents(claims['sub'])}

@router.get('/chat/documents/{document_id}/outline')
def chat_document_outline(document_id:str,claims=Depends(get_claims)):
    workspace=DocumentWorkspace(ai_service.intelligence.rag.store)
    result=workspace.outline(document_id,claims['sub'])
    if not result: raise HTTPException(404,'المستند غير موجود أو لا تملك صلاحية الوصول إليه')
    return result

class DocumentCompare(BaseModel):
    document_ids:list[str]=Field(min_length=2,max_length=5)
    question:str=Field(min_length=2,max_length=12000)

@router.post('/chat/documents/compare')
def compare_chat_documents(payload:DocumentCompare,claims=Depends(get_claims)):
    workspace=DocumentWorkspace(ai_service.intelligence.rag.store)
    result=workspace.compare(payload.document_ids,claims['sub'],payload.question)
    if not result: raise HTTPException(404,'أحد المستندات غير موجود أو لا تملك صلاحية الوصول إليه')
    return result


class DocumentStudyPlan(BaseModel):
    days:int=Field(default=7,ge=1,le=60)

@router.get('/chat/documents/{document_id}/summary')
def document_summary(document_id:str,claims=Depends(get_claims)):
    result=DocumentResearch(ai_service.intelligence.rag.store).summary(document_id,claims['sub'])
    if not result: raise HTTPException(404,'المستند غير موجود أو لا تملك صلاحية الوصول إليه')
    return result

@router.get('/chat/documents/{document_id}/key-points')
def document_key_points(document_id:str,limit:int=12,claims=Depends(get_claims)):
    result=DocumentResearch(ai_service.intelligence.rag.store).key_points(document_id,claims['sub'],max(1,min(limit,30)))
    if not result: raise HTTPException(404,'المستند غير موجود أو لا تملك صلاحية الوصول إليه')
    return result

@router.post('/chat/documents/{document_id}/study-plan')
def document_study_plan(document_id:str,payload:DocumentStudyPlan,claims=Depends(get_claims)):
    result=DocumentResearch(ai_service.intelligence.rag.store).study_plan(document_id,claims['sub'],payload.days)
    if not result: raise HTTPException(404,'المستند غير موجود أو لا تملك صلاحية الوصول إليه')
    return result

@router.get('/chat/documents/{document_id}/quiz')
def document_quiz(document_id:str,limit:int=8,claims=Depends(get_claims)):
    result=DocumentResearch(ai_service.intelligence.rag.store).quiz(document_id,claims['sub'],max(1,min(limit,20)))
    if not result: raise HTTPException(404,'المستند غير موجود أو لا تملك صلاحية الوصول إليه')
    return result

@router.get('/chat/documents/search')
def document_search(q:str,document_ids:str,limit:int=12,claims=Depends(get_claims)):
    ids=[x.strip() for x in document_ids.split(',') if x.strip()][:10]
    if not ids: raise HTTPException(400,'يجب تحديد مستند واحد على الأقل')
    result=DocumentResearch(ai_service.intelligence.rag.store).search(ids,claims['sub'],q,max(1,min(limit,50)))
    if result is None: raise HTTPException(404,'أحد المستندات غير موجود أو لا تملك صلاحية الوصول إليه')
    return result

@router.post('/chat')
def chat(payload:Chat,claims=Depends(get_claims)):
    session_id=f"{claims['sub']}:{payload.session_id}"
    if payload.document_id:
        owned=any(x.get('metadata',{}).get('document_id')==payload.document_id and x.get('metadata',{}).get('owner')==claims['sub'] for x in ai_service.intelligence.rag.store.items)
        if not owned: raise HTTPException(404,'المستند غير موجود أو لا تملك صلاحية الوصول إليه')
    result=ai_service.respond(payload.message,session_id,document_id=payload.document_id,document_owner=claims['sub']);add_activity(claims['role'],'chat',payload.message[:120]);return result
@router.post('/chat/feedback')
def chat_feedback(payload:ChatFeedback,claims=Depends(get_claims)):
    sid=f"{claims['sub']}:{payload.session_id}"
    fid=add_answer_feedback(sid,payload.message,payload.answer,payload.rating,payload.notes.strip())
    # Explicit correction notes are preserved as local knowledge only when the user gives a poor
    # rating and actually supplies a correction. This avoids blindly learning every preference.
    learned=False
    if payload.rating<=2 and len(payload.notes.strip())>=12:
        kid=add_knowledge('تصحيح محادثة: '+payload.message[:120],payload.notes.strip(),'user_correction')
        ai_service.intelligence.rag.store.add(payload.notes.strip(),{'source':'user_correction','knowledge_id':kid,'title':'تصحيح محادثة','training_artifact':'feedback_correction'})
        learned=True
    add_activity(claims['role'],'chat_feedback',f'rating={payload.rating}')
    return {'id':fid,'saved':True,'learned_correction':learned}

@router.get('/conversations/{session_id}')
def history(session_id:str,claims=Depends(get_claims)):
    sid=f"{claims['sub']}:{session_id}" if claims['role']!='admin' else session_id
    return conversation_history(sid[:128])
@router.delete('/conversations/{session_id}')
def clear_history(session_id:str,claims=Depends(get_claims)):
    sid=f"{claims['sub']}:{session_id}" if claims['role']!='admin' else session_id
    deleted=clear_conversation(sid[:128]); add_activity(claims['role'],'conversation_cleared',sid[:120]); return {'message':'Conversation cleared','deleted':deleted}
@router.get('/seed/status')
def seed_status_api(claims=Depends(require('admin','developer','trainer'))):
    return seed_status()

@router.post('/seed/import')
def seed_import_api(force:bool=False,claims=Depends(require('admin','developer','trainer'))):
    result=import_seed_knowledge(force=force)
    add_activity(claims['role'],'seed_import_requested',str(result))
    return result

@router.get('/export/activities.csv')
def export_activities(claims=Depends(require('admin','developer'))):
    rows=list_activities(10000);out=io.StringIO();w=csv.DictWriter(out,fieldnames=['id','portal','action','details','created_at']);w.writeheader();w.writerows(rows)
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=activities.csv'})


@router.get('/users')
def users(claims=Depends(require('admin'))):
    return list_users()

@router.post('/users')
def user_create(payload:UserCreate,claims=Depends(require('admin'))):
    if payload.role not in VALID_ROLES: raise HTTPException(400,'Invalid role')
    user_id=create_user_safe(payload.username,hash_password(payload.password),payload.role)
    if user_id is None: raise HTTPException(409,'Username already exists')
    add_activity('admin','user_created',payload.username); add_system_event('info','user_created',payload.username)
    return {'id':user_id,'message':'User created successfully'}

@router.patch('/users/{user_id}/role')
def user_role(user_id:int,payload:RoleUpdate,claims=Depends(require('admin'))):
    if payload.role not in VALID_ROLES: raise HTTPException(400,'Invalid role')
    target=get_user_by_id(user_id)
    if not target: raise HTTPException(404,'User not found')
    if target['username']==claims['sub'] and payload.role!='admin': raise HTTPException(400,'Cannot remove your own admin role')
    if not update_user_role(user_id,payload.role): raise HTTPException(404,'User not found')
    add_activity('admin','user_role_updated',target['username']+' -> '+payload.role)
    return {'message':'Role updated'}

@router.delete('/users/{user_id}')
def user_delete(user_id:int,claims=Depends(require('admin'))):
    target=get_user_by_id(user_id)
    if not target: raise HTTPException(404,'User not found')
    if target['username']==claims['sub']: raise HTTPException(400,'Cannot delete your own account')
    if not delete_user(user_id): raise HTTPException(404,'User not found')
    add_activity('admin','user_deleted',target['username']); add_system_event('warning','user_deleted',target['username'])
    return {'message':'User deleted'}

@router.get('/settings')
def settings(claims=Depends(require('admin','developer'))):
    return {'items':list_settings(),'defaults':{'app_name':'Yemen AI','maintenance_mode':False}}

@router.put('/settings/{key}')
def setting_update(key:str,payload:SettingUpdate,claims=Depends(require('admin'))):
    if not key.replace('_','').replace('-','').isalnum() or len(key)>64: raise HTTPException(400,'Invalid setting key')
    set_setting(key,payload.value); add_activity('admin','setting_updated',key)
    return {'message':'Setting saved','key':key,'value':payload.value}

@router.get('/system/events')
def system_events(claims=Depends(require('admin','developer'))):
    return list_system_events()
