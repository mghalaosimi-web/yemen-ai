import sqlite3, json
from app.core.config import DB_PATH

def connect():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def initialize_database():
    with connect() as c:
      c.executescript('''
      CREATE TABLE IF NOT EXISTS datasets(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,description TEXT DEFAULT '',filename TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS activities(id INTEGER PRIMARY KEY AUTOINCREMENT,portal TEXT NOT NULL,action TEXT NOT NULL,details TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS knowledge(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,content TEXT NOT NULL,source TEXT DEFAULT 'manual',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY AUTOINCREMENT,session_id TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS api_keys(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,key_hash TEXT NOT NULL,active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'user',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS ingestion_jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,dataset_id INTEGER,filename TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',chunks INTEGER DEFAULT 0,error TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP,completed_at TEXT DEFAULT '');
      CREATE TABLE IF NOT EXISTS system_events(id INTEGER PRIMARY KEY AUTOINCREMENT,level TEXT NOT NULL DEFAULT 'info',event TEXT NOT NULL,details TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY AUTOINCREMENT,session_id TEXT NOT NULL,memory_type TEXT NOT NULL DEFAULT 'context',content TEXT NOT NULL,importance REAL DEFAULT 0.5,metadata TEXT DEFAULT '{}',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS answer_feedback(id INTEGER PRIMARY KEY AUTOINCREMENT,session_id TEXT NOT NULL,message TEXT NOT NULL,answer TEXT NOT NULL,rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),notes TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS training_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,dataset_id INTEGER NOT NULL,actor TEXT DEFAULT '',status TEXT NOT NULL DEFAULT 'queued',chunks INTEGER DEFAULT 0,error TEXT DEFAULT '',metrics TEXT DEFAULT '{}',created_at TEXT DEFAULT CURRENT_TIMESTAMP,completed_at TEXT DEFAULT '');
      CREATE TABLE IF NOT EXISTS graph_nodes(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,node_type TEXT NOT NULL DEFAULT 'concept',metadata TEXT DEFAULT '{}',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS graph_edges(id INTEGER PRIMARY KEY AUTOINCREMENT,source_id INTEGER NOT NULL,target_id INTEGER NOT NULL,relation TEXT NOT NULL DEFAULT 'related_to',weight REAL DEFAULT 1.0,metadata TEXT DEFAULT '{}',created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(source_id,target_id,relation));
      CREATE TABLE IF NOT EXISTS graph_sources(id INTEGER PRIMARY KEY AUTOINCREMENT,node_id INTEGER NOT NULL,source_ref TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);

      -- v10.1 Personal Knowledge & Bilingual Knowledge Extensions
      CREATE TABLE IF NOT EXISTS personal_facts(id INTEGER PRIMARY KEY AUTOINCREMENT, fact_id TEXT UNIQUE NOT NULL, subject TEXT NOT NULL, predicate TEXT NOT NULL, object TEXT NOT NULL, domain TEXT NOT NULL, language TEXT DEFAULT 'en', confidence REAL DEFAULT 1.0, source_id TEXT DEFAULT '', source_type TEXT DEFAULT 'personal_context', source_section TEXT DEFAULT '', visibility TEXT DEFAULT 'private', status TEXT DEFAULT 'active', created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, superseded_by TEXT DEFAULT '', version INTEGER DEFAULT 1);
      CREATE TABLE IF NOT EXISTS personal_fact_versions(id INTEGER PRIMARY KEY AUTOINCREMENT, version_id TEXT UNIQUE NOT NULL, fact_id TEXT NOT NULL, value TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, superseded_at TEXT DEFAULT '', source_id TEXT DEFAULT '');
      CREATE TABLE IF NOT EXISTS knowledge_versions(id INTEGER PRIMARY KEY AUTOINCREMENT, version_id TEXT UNIQUE NOT NULL, knowledge_id TEXT NOT NULL, previous_version_id TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'active', value TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, superseded_at TEXT DEFAULT '', source_id TEXT DEFAULT '');
      CREATE TABLE IF NOT EXISTS knowledge_sources(id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT UNIQUE NOT NULL, source_type TEXT NOT NULL, location TEXT DEFAULT '', status TEXT DEFAULT 'active', metadata TEXT DEFAULT '{}', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS knowledge_conflicts(id INTEGER PRIMARY KEY AUTOINCREMENT, conflict_id TEXT UNIQUE NOT NULL, item_a_id TEXT NOT NULL, item_b_id TEXT NOT NULL, domain TEXT DEFAULT '', description TEXT DEFAULT '', status TEXT DEFAULT 'unresolved', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS knowledge_packs(id INTEGER PRIMARY KEY AUTOINCREMENT, pack_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL, version TEXT DEFAULT '1.0', domain TEXT NOT NULL, language TEXT DEFAULT 'en', source TEXT DEFAULT '', scope TEXT DEFAULT 'public', checksum TEXT DEFAULT '', status TEXT DEFAULT 'active', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS project_states(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL, description TEXT DEFAULT '', current_version TEXT DEFAULT '10.1', status TEXT DEFAULT 'active', architecture TEXT DEFAULT '', metadata TEXT DEFAULT '{}', updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS project_versions(id INTEGER PRIMARY KEY AUTOINCREMENT, id_str TEXT UNIQUE NOT NULL, project_id TEXT NOT NULL, version TEXT NOT NULL, summary TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS project_issues(id INTEGER PRIMARY KEY AUTOINCREMENT, issue_id TEXT UNIQUE NOT NULL, project_id TEXT NOT NULL, title TEXT NOT NULL, status TEXT DEFAULT 'open', priority TEXT DEFAULT 'medium', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS project_tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT UNIQUE NOT NULL, project_id TEXT NOT NULL, title TEXT NOT NULL, status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS user_interaction_profiles(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT UNIQUE NOT NULL, preferred_response_language TEXT DEFAULT 'ar', preferred_detail_level TEXT DEFAULT 'medium', technical_depth TEXT DEFAULT 'high', communication_style TEXT DEFAULT 'direct', preferred_answer_format TEXT DEFAULT 'structured', active_projects TEXT DEFAULT '[]', frequently_used_terms TEXT DEFAULT '[]', updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS bilingual_concepts(id INTEGER PRIMARY KEY AUTOINCREMENT, concept_id TEXT UNIQUE NOT NULL, canonical_id TEXT NOT NULL, labels_json TEXT DEFAULT '{}', aliases_json TEXT DEFAULT '[]', definitions_json TEXT DEFAULT '{}', related_json TEXT DEFAULT '[]', updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS bilingual_aliases(alias TEXT NOT NULL, concept_id TEXT NOT NULL, language TEXT DEFAULT 'en', PRIMARY KEY (alias, concept_id));
      CREATE TABLE IF NOT EXISTS training_reports(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT UNIQUE NOT NULL, documents_processed INTEGER DEFAULT 0, chunks_created INTEGER DEFAULT 0, concepts_created INTEGER DEFAULT 0, relationships_created INTEGER DEFAULT 0, bilingual_links_created INTEGER DEFAULT 0, duplicates_skipped INTEGER DEFAULT 0, conflicts_detected INTEGER DEFAULT 0, failures INTEGER DEFAULT 0, duration_seconds REAL DEFAULT 0.0, status TEXT DEFAULT 'completed', details_json TEXT DEFAULT '{}', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS batch_training_jobs(id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT UNIQUE NOT NULL, status TEXT DEFAULT 'pending', total_sources INTEGER DEFAULT 0, processed_sources INTEGER DEFAULT 0, successful_sources INTEGER DEFAULT 0, failed_sources INTEGER DEFAULT 0, current_source TEXT DEFAULT '', started_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, completed_at TEXT DEFAULT '');

      CREATE INDEX IF NOT EXISTS idx_pf_domain ON personal_facts(domain);
      CREATE INDEX IF NOT EXISTS idx_pf_status ON personal_facts(status);
      CREATE INDEX IF NOT EXISTS idx_pf_visibility ON personal_facts(visibility);
      CREATE INDEX IF NOT EXISTS idx_kp_domain ON knowledge_packs(domain);
      CREATE INDEX IF NOT EXISTS idx_kp_scope ON knowledge_packs(scope);
      CREATE INDEX IF NOT EXISTS idx_ks_source ON knowledge_sources(source_id);
      ''')

def add_activity(portal,action,details=''):
    with connect() as c:c.execute('INSERT INTO activities(portal,action,details) VALUES (?,?,?)',(portal,action,details))
def create_dataset(name,description='',filename=''):
    with connect() as c:return c.execute('INSERT INTO datasets(name,description,filename) VALUES (?,?,?)',(name,description,filename)).lastrowid
def list_datasets():
    with connect() as c:return [dict(x) for x in c.execute('SELECT * FROM datasets ORDER BY id DESC').fetchall()]
def list_activities(limit=100):
    with connect() as c:return [dict(x) for x in c.execute('SELECT * FROM activities ORDER BY id DESC LIMIT ?',(limit,)).fetchall()]
def add_knowledge(title,content,source='manual'):
    with connect() as c:return c.execute('INSERT INTO knowledge(title,content,source) VALUES (?,?,?)',(title,content,source)).lastrowid
def search_knowledge(query,limit=5):
    q=f'%{query}%'
    with connect() as c:return [dict(x) for x in c.execute('SELECT * FROM knowledge WHERE title LIKE ? OR content LIKE ? ORDER BY id DESC LIMIT ?',(q,q,limit)).fetchall()]
def list_knowledge():
    with connect() as c:return [dict(x) for x in c.execute('SELECT * FROM knowledge ORDER BY id DESC').fetchall()]
def save_message(session_id,role,content):
    with connect() as c:c.execute('INSERT INTO conversations(session_id,role,content) VALUES (?,?,?)',(session_id,role,content))
def conversation_history(session_id,limit=20):
    with connect() as c:return [dict(x) for x in c.execute('SELECT * FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT ?',(session_id,limit)).fetchall()][::-1]
def stats():
    with connect() as c:
      return {k:c.execute(f'SELECT COUNT(*) n FROM {t}').fetchone()['n'] for k,t in {'datasets':'datasets','activities':'activities','knowledge':'knowledge','messages':'conversations'}.items()}


def get_user(username):
    with connect() as c:
        r=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone(); return dict(r) if r else None
def create_user(username,password_hash,role='user'):
    with connect() as c:return c.execute('INSERT INTO users(username,password_hash,role) VALUES (?,?,?)',(username,password_hash,role)).lastrowid
def list_users():
    with connect() as c:return [dict(x) for x in c.execute('SELECT id,username,role,created_at FROM users ORDER BY id').fetchall()]


def ensure_demo_users(password_hash, repair_existing=False):
    """Create missing demo users and optionally repair prototype credentials.

    repair_existing is intended only for local development so an older prototype
    database cannot leave the documented demo accounts permanently unusable.
    Production keeps existing credentials untouched.
    """
    demo=[('admin','admin'),('developer','developer'),('trainer','trainer'),('user','user')]
    with connect() as c:
        for username,role in demo:
            row=c.execute('SELECT id,password_hash,role FROM users WHERE username=?',(username,)).fetchone()
            if not row:
                c.execute('INSERT INTO users(username,password_hash,role) VALUES (?,?,?)',(username,password_hash,role))
            elif repair_existing and row['role']==role and row['password_hash']!=password_hash:
                c.execute('UPDATE users SET password_hash=? WHERE id=?',(password_hash,row['id']))


def latest_dataset_by_filename(filename):
    with connect() as c:
        r=c.execute('SELECT * FROM datasets WHERE filename=? ORDER BY id DESC LIMIT 1',(filename,)).fetchone(); return dict(r) if r else None
def create_ingestion_job(dataset_id,filename):
    with connect() as c:return c.execute("INSERT INTO ingestion_jobs(dataset_id,filename,status) VALUES (?,?, 'processing')",(dataset_id,filename)).lastrowid
def complete_ingestion_job(job_id,chunks):
    with connect() as c:c.execute("UPDATE ingestion_jobs SET status='completed',chunks=?,completed_at=CURRENT_TIMESTAMP WHERE id=?",(chunks,job_id))
def fail_ingestion_job(job_id,error):
    with connect() as c:c.execute("UPDATE ingestion_jobs SET status='failed',error=?,completed_at=CURRENT_TIMESTAMP WHERE id=?",(str(error)[:1000],job_id))
def list_ingestion_jobs(limit=50):
    with connect() as c:return [dict(x) for x in c.execute('SELECT * FROM ingestion_jobs ORDER BY id DESC LIMIT ?',(limit,)).fetchall()]

def delete_dataset(dataset_id):
    with connect() as c:
        cur=c.execute('DELETE FROM datasets WHERE id=?',(dataset_id,)); return cur.rowcount

def delete_knowledge(knowledge_id):
    with connect() as c:
        cur=c.execute('DELETE FROM knowledge WHERE id=?',(knowledge_id,)); return cur.rowcount

def clear_conversation(session_id):
    with connect() as c:
        cur=c.execute('DELETE FROM conversations WHERE session_id=?',(session_id,)); return cur.rowcount


def create_user_safe(username,password_hash,role='user'):
    with connect() as c:
        try:
            return c.execute('INSERT INTO users(username,password_hash,role) VALUES (?,?,?)',(username,password_hash,role)).lastrowid
        except sqlite3.IntegrityError:
            return None

def update_user_role(user_id,role):
    with connect() as c:
        cur=c.execute('UPDATE users SET role=? WHERE id=?',(role,user_id)); return cur.rowcount

def delete_user(user_id):
    with connect() as c:
        cur=c.execute('DELETE FROM users WHERE id=?',(user_id,)); return cur.rowcount

def get_user_by_id(user_id):
    with connect() as c:
        r=c.execute('SELECT id,username,role,created_at FROM users WHERE id=?',(user_id,)).fetchone(); return dict(r) if r else None

def set_setting(key,value):
    with connect() as c:
        c.execute("INSERT INTO settings(key,value,updated_at) VALUES (?,?,CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP",(key,json.dumps(value,ensure_ascii=False)))

def get_setting(key,default=None):
    with connect() as c:
        r=c.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
    if not r:return default
    try:return json.loads(r['value'])
    except Exception:return r['value']

def list_settings():
    with connect() as c:
        rows=c.execute('SELECT key,value,updated_at FROM settings ORDER BY key').fetchall()
    out=[]
    for r in rows:
        d=dict(r)
        try:d['value']=json.loads(d['value'])
        except Exception:pass
        out.append(d)
    return out

def add_system_event(level,event,details=''):
    with connect() as c:c.execute('INSERT INTO system_events(level,event,details) VALUES (?,?,?)',(level,event,details))

def list_system_events(limit=100):
    with connect() as c:return [dict(x) for x in c.execute('SELECT * FROM system_events ORDER BY id DESC LIMIT ?',(limit,)).fetchall()]


def get_dataset(dataset_id):
 with connect() as c:
  r=c.execute('SELECT * FROM datasets WHERE id=?',(dataset_id,)).fetchone(); return dict(r) if r else None
def create_training_run(dataset_id,actor,status='queued'):
 with connect() as c:return c.execute('INSERT INTO training_runs(dataset_id,actor,status) VALUES (?,?,?)',(dataset_id,actor,status)).lastrowid
def update_training_run(run_id,status,chunks=0,error='',metrics=None):
 with connect() as c:c.execute("UPDATE training_runs SET status=?,chunks=?,error=?,metrics=?,completed_at=CURRENT_TIMESTAMP WHERE id=?",(status,chunks,str(error)[:1000],json.dumps(metrics or {},ensure_ascii=False),run_id))
def list_training_runs(limit=50):
 with connect() as c: rows=[dict(x) for x in c.execute('SELECT * FROM training_runs ORDER BY id DESC LIMIT ?',(limit,)).fetchall()]
 for r in rows:
  try:r['metrics']=json.loads(r.get('metrics') or '{}')
  except Exception:r['metrics']={}
 return rows
def training_stats():
 with connect() as c:
  total=c.execute('SELECT COUNT(*) n FROM training_runs').fetchone()['n']; done=c.execute("SELECT COUNT(*) n FROM training_runs WHERE status='completed'").fetchone()['n']; failed=c.execute("SELECT COUNT(*) n FROM training_runs WHERE status='failed'").fetchone()['n']; chunks=c.execute("SELECT COALESCE(SUM(chunks),0) n FROM training_runs WHERE status='completed'").fetchone()['n']
 return {'total_runs':total,'completed':done,'failed':failed,'chunks_processed':chunks}

# v7.5 memory + answer quality layer
def save_memory(session_id, memory_type, content, importance=0.5, metadata=None):
    metadata = json.dumps(metadata or {}, ensure_ascii=False)
    with connect() as c:
        return c.execute('INSERT INTO memories(session_id,memory_type,content,importance,metadata) VALUES (?,?,?,?,?)',
                         (session_id,memory_type,content,float(importance),metadata)).lastrowid

def recent_memories(session_id, limit=8):
    with connect() as c:
        rows=c.execute('SELECT * FROM memories WHERE session_id=? ORDER BY importance DESC,id DESC LIMIT ?', (session_id,limit)).fetchall()
    out=[]
    for r in rows:
        d=dict(r)
        try:d['metadata']=json.loads(d.get('metadata') or '{}')
        except Exception:d['metadata']={}
        out.append(d)
    return out

def clear_memories(session_id):
    with connect() as c:
        return c.execute('DELETE FROM memories WHERE session_id=?',(session_id,)).rowcount

def add_answer_feedback(session_id, message, answer, rating, notes=''):
    with connect() as c:
        return c.execute('INSERT INTO answer_feedback(session_id,message,answer,rating,notes) VALUES (?,?,?,?,?)',
                         (session_id,message,answer,int(rating),notes)).lastrowid

def memory_stats(session_id=None):
    with connect() as c:
        if session_id:
            m=c.execute('SELECT COUNT(*) n FROM memories WHERE session_id=?',(session_id,)).fetchone()['n']
            f=c.execute('SELECT COUNT(*) n FROM answer_feedback WHERE session_id=?',(session_id,)).fetchone()['n']
        else:
            m=c.execute('SELECT COUNT(*) n FROM memories').fetchone()['n']
            f=c.execute('SELECT COUNT(*) n FROM answer_feedback').fetchone()['n']
    return {'memories':m,'feedback':f}


# v8.0 knowledge graph
def upsert_graph_node(name,node_type='concept',metadata=None):
    initialize_database()
    name=' '.join(str(name).strip().split())[:200]
    if not name: return None
    payload=json.dumps(metadata or {},ensure_ascii=False)
    with connect() as c:
        c.execute("INSERT INTO graph_nodes(name,node_type,metadata) VALUES (?,?,?) ON CONFLICT(name) DO UPDATE SET node_type=excluded.node_type,metadata=excluded.metadata",(name,node_type,payload))
        return c.execute('SELECT id FROM graph_nodes WHERE name=?',(name,)).fetchone()['id']

def upsert_graph_edge(source_id,target_id,relation='related_to',weight=1.0,metadata=None):
    initialize_database()
    if not source_id or not target_id or source_id==target_id:return None
    if source_id>target_id: source_id,target_id=target_id,source_id
    payload=json.dumps(metadata or {},ensure_ascii=False)
    with connect() as c:
        c.execute("INSERT INTO graph_edges(source_id,target_id,relation,weight,metadata) VALUES (?,?,?,?,?) ON CONFLICT(source_id,target_id,relation) DO UPDATE SET weight=MAX(graph_edges.weight,excluded.weight),metadata=excluded.metadata",(source_id,target_id,relation,float(weight),payload))
        return c.execute('SELECT id FROM graph_edges WHERE source_id=? AND target_id=? AND relation=?',(source_id,target_id,relation)).fetchone()['id']

def graph_overview(limit=300):
    initialize_database()
    with connect() as c:
        nodes=[dict(x) for x in c.execute('SELECT id,name,node_type,metadata,created_at FROM graph_nodes ORDER BY id DESC LIMIT ?',(limit,)).fetchall()]
        edges=[dict(x) for x in c.execute('SELECT * FROM graph_edges ORDER BY weight DESC,id DESC LIMIT ?',(limit*2,)).fetchall()]
    return {'nodes':nodes,'edges':edges,'stats':{'nodes':len(nodes),'edges':len(edges)}}

def graph_search(query,limit=20):
    initialize_database()
    q=f'%{query.strip()}%'
    with connect() as c:
        return [dict(x) for x in c.execute('SELECT * FROM graph_nodes WHERE name LIKE ? ORDER BY name LIMIT ?',(q,limit)).fetchall()]

def clear_graph():
    initialize_database()
    with connect() as c:
        e=c.execute('DELETE FROM graph_edges').rowcount; n=c.execute('DELETE FROM graph_nodes').rowcount
    return {'nodes':n,'edges':e}
