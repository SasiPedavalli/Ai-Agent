from __future__ import annotations
import json,re,sqlite3,uuid
from dataclasses import dataclass,field
from pathlib import Path
from typing import Any
from prime_genesis.models import utc_now
from prime_genesis.security import TenantContext,require_role
TOKEN=re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]+')
@dataclass(frozen=True)
class DocumentRecord:
 document_id:str;tenant_id:str;namespace:str;title:str;content:str;metadata:dict[str,Any]=field(default_factory=dict);created_at:str=field(default_factory=utc_now)
@dataclass(frozen=True)
class RetrievalHit:
 document:DocumentRecord;score:float;matched_terms:tuple[str,...]
SCHEMA="""CREATE TABLE IF NOT EXISTS documents (document_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,namespace TEXT NOT NULL,title TEXT NOT NULL,content TEXT NOT NULL,metadata_json TEXT NOT NULL,created_at TEXT NOT NULL);CREATE INDEX IF NOT EXISTS idx_documents_tenant_namespace ON documents (tenant_id,namespace,created_at);"""
class TenantDocumentStore:
 def __init__(self,path:str|Path)->None:self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.connection=sqlite3.connect(self.path);self.connection.row_factory=sqlite3.Row;self.connection.executescript(SCHEMA)
 def close(self)->None:self.connection.close()
 @staticmethod
 def _tokens(text:str)->set[str]:return {t.lower() for t in TOKEN.findall(text) if len(t)>1}
 @staticmethod
 def _record(row:sqlite3.Row)->DocumentRecord:return DocumentRecord(row['document_id'],row['tenant_id'],row['namespace'],row['title'],row['content'],json.loads(row['metadata_json']),row['created_at'])
 def add(self,context:TenantContext,*,namespace:str,title:str,content:str,metadata:dict[str,Any]|None=None)->DocumentRecord:
  require_role(context,'writer','admin')
  if not namespace.strip() or not title.strip() or not content.strip():raise ValueError('namespace, title, and content are required')
  record=DocumentRecord(f"doc-{uuid.uuid4().hex[:16]}",context.tenant_id,namespace.strip(),title.strip(),content.strip(),metadata or {});self.connection.execute('INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)',(record.document_id,record.tenant_id,record.namespace,record.title,record.content,json.dumps(record.metadata,sort_keys=True),record.created_at));self.connection.commit();return record
 def search(self,context:TenantContext,*,query:str,namespace:str|None=None,limit:int=5)->list[RetrievalHit]:
  rows=self.connection.execute('SELECT * FROM documents WHERE tenant_id=?'+(' AND namespace=?' if namespace is not None else ''),(context.tenant_id,namespace) if namespace is not None else (context.tenant_id,)).fetchall();q=self._tokens(query);hits=[]
  for row in rows:
   doc=self._record(row);matched=tuple(sorted(q.intersection(self._tokens(f'{doc.title} {doc.content}'))))
   if matched:hits.append(RetrievalHit(doc,len(matched)/max(1,len(q)),matched))
  return sorted(hits,key=lambda h:(-h.score,h.document.created_at))[:min(max(limit,1),50)]
