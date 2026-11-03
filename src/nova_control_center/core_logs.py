"""SQLite WAL structured logbook for NOVA Core.

Write scalar/typed metadata only; never log arbitrary request bodies, commands
or secrets. Audit entries cannot be disabled through UI preferences.
"""
from __future__ import annotations
import json
import os
import re
import sqlite3
import threading
from datetime import datetime,timezone,timedelta
from pathlib import Path
from .core_settings import xdg_data

ALLOWED={"DEBUG","INFO","WARNING","ERROR","AUDIT"}
SENSITIVE=re.compile(r"(?i)(bearer\s+\S+|(?:token|password|secret|apikey|api_key|authorization|passphrase)\s*[:=]\s*\S+)")
KEYS={"password","passphrase","token","secret","authorization","cookie","api_key","apikey","private_key","ssh_key","key_material"}
def scrub(value):
    s=str(value)
    return SENSITIVE.sub("[REDACTED]",s)[:1600]
def safe_meta(data):
    if not isinstance(data,dict):
        return {}
    out={}
    for k,v in list(data.items())[:25]:
        key=str(k)[:80]
        if any(term in key.lower() for term in KEYS):
            out[key]="[REDACTED]"
        elif isinstance(v,(str,int,float,bool)) or v is None:
            out[key]=scrub(v) if isinstance(v,str) else v
    return out

class LogStore:
    def __init__(self,path=None):
        self.path=Path(path) if path else xdg_data()/"logs.sqlite3"
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        try:os.chmod(self.path.parent,0o700)
        except OSError:pass
        self._lock=threading.RLock()
        self._db=sqlite3.connect(str(self.path),check_same_thread=False,timeout=4)
        self._db.execute("PRAGMA busy_timeout=4000")
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.execute("CREATE TABLE IF NOT EXISTS entries ("
                         "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                         "ts TEXT NOT NULL, level TEXT NOT NULL,"
                         "source TEXT NOT NULL, event TEXT NOT NULL,"
                         "message TEXT NOT NULL, session_id TEXT,"
                         "metadata TEXT NOT NULL DEFAULT '{}')")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_entries_ts ON entries(ts)")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_entries_source ON entries(source,level)")
        self._db.commit()
        if self.path.exists():
            try:self.path.chmod(0o600)
            except OSError:pass

    def write(self,level,source,event,message="",session_id=None,metadata=None):
        level=str(level).upper()
        if level not in ALLOWED:raise ValueError("Invalid log level")
        with self._lock:
            self._db.execute(
                "INSERT INTO entries(ts,level,source,event,message,session_id,metadata) "
                "VALUES(?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                 level,scrub(source)[:80],scrub(event)[:120],scrub(message),
                 scrub(session_id)[:120] if session_id else None,
                 json.dumps(safe_meta(metadata),ensure_ascii=False)))
            self._db.commit()

    def recent(self,limit=200,level=None,source=None,contains=None):
        clauses=[]
        args=[]
        if level:
            clauses.append("level=?")
            args.append(str(level).upper())
        if source:
            clauses.append("source=?")
            args.append(str(source))
        if contains:
            clauses.append("message LIKE ? ESCAPE '\\'")
            value=str(contains).replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
            args.append("%"+value[:100]+"%")
        sql="SELECT id,ts,level,source,event,message,session_id,metadata FROM entries"
        if clauses:sql+=" WHERE "+" AND ".join(clauses)
        sql+=" ORDER BY id DESC LIMIT ?"
        args.append(max(1,min(1000,int(limit))))
        with self._lock:
            rows=self._db.execute(sql,args).fetchall()
        return [dict(zip(("id","ts","level","source","event","message","session_id","metadata"),r)) for r in rows]

    def prune(self,days=30,max_rows=100000):
        cutoff=(datetime.now(timezone.utc)-timedelta(days=max(1,int(days)))).isoformat()
        with self._lock:
            self._db.execute("DELETE FROM entries WHERE ts < ?",(cutoff,))
            # Keep latest N rows; bounded without relying on rowid VACUUM.
            self._db.execute(
                "DELETE FROM entries WHERE id IN "
                "(SELECT id FROM entries ORDER BY id DESC LIMIT -1 OFFSET ?)",
                (max(1000,int(max_rows)),))
            self._db.commit()

    def close(self):
        with self._lock:self._db.close()
