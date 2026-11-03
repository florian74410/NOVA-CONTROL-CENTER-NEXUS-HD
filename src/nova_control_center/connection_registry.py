"""NOVA Core: per-OS-user connection profile registry, no secrets in JSON.

The active OS account is the owner of the NOVA session; 'administrator' is
descriptive and does NOT grant process privileges or remote authentication.
"""
from __future__ import annotations
import pwd
import json
import os
import re
import socket
import stat
import tempfile
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
from .core_settings import xdg_config
from .suite_profile import SuiteProfileStore

PROTOCOLS=("FTP","SSH","HTTPS","MYSQL","SQLITE","SMTP","TCP")
DEFAULT_PORT={"FTP":21,"SSH":22,"HTTPS":443,"MYSQL":3306,"SMTP":465,"TCP":0}
ALLOWED={
 "FTP":{"host","port","username","mode","remote_dir","timeout"},
 "SSH":{"host","port","username","identity","timeout"},
 "HTTPS":{"url","method","credential_ref","timeout"},
 "MYSQL":{"host","port","username","database","tls","credential_ref","timeout"},
 "SQLITE":{"path","readonly","timeout"},
 "SMTP":{"host","port","username","tls","credential_ref","timeout"},
 "TCP":{"host","port","timeout"},
}
SECRET_NAMES={"password","token","secret","passphrase","authorization","private_key","api_key","cookie"}
ID=re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
HOST=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,252}$")

@dataclass(frozen=True)
class MachineIdentity:
    username:str
    uid:int
    home:str
    administrator:bool

    @staticmethod
    def current():
        import grp
        uid=os.geteuid()
        name=pwd.getpwuid(uid).pw_name
        groups=set(os.getgroups())
        admin_groups={"sudo","wheel","admin"}
        admin=uid==0 or any(g.gr_name in admin_groups and g.gr_gid in groups for g in grp.getgrall())
        return MachineIdentity(name,uid,str(Path.home()),admin)

@dataclass(frozen=True)
class ConnectionDefinition:
    connection_id:str
    name:str
    protocol:str
    options:dict[str,Any]=field(default_factory=dict)

def normalize(obj):
    if not isinstance(obj,ConnectionDefinition):
        raise TypeError("ConnectionDefinition expected")
    if obj.protocol not in PROTOCOLS:
        raise ValueError("Unknown connection protocol")
    if not isinstance(obj.name,str) or not 1<=len(obj.name.strip())<=80:
        raise ValueError("Connection name required")
    if not isinstance(obj.options,dict):
        raise ValueError("Options must be a mapping")
    if set(obj.options)-ALLOWED[obj.protocol]:
        raise ValueError("Unsupported or secret-bearing option")
    for k,v in obj.options.items():
        if any(secret in k.lower() for secret in SECRET_NAMES):
            raise ValueError("Secret material is not permitted in profile JSON")
        if isinstance(v,(dict,list,bytes)) or (isinstance(v,str) and len(v)>1024):
            raise ValueError("Invalid option value")
    settings=dict(obj.options)
    if obj.protocol=="SQLITE":
        path=str(settings.get("path","")).strip()
        if not path:raise ValueError("SQLite file path required")
        settings["path"]=str(Path(path).expanduser())
        settings["readonly"]=bool(settings.get("readonly",True))
    elif obj.protocol=="HTTPS":
        from urllib.parse import urlsplit
        url=str(settings.get("url","")).strip()
        split=urlsplit(url)
        if split.scheme!="https" or not split.hostname or split.username or split.password or split.query or split.fragment:
            raise ValueError("HTTPS URL must not contain credentials or query secrets")
        settings["url"]=url
        if settings.get("method","HEAD") not in ("HEAD","GET"):
            raise ValueError("HTTP method must be HEAD or GET")
    else:
        host=str(settings.get("host","")).strip()
        if not HOST.fullmatch(host):raise ValueError("Host required")
        settings["host"]=host
        port=int(settings.get("port",DEFAULT_PORT[obj.protocol]))
        if not 1<=port<=65535:raise ValueError("Port must be 1–65535")
        settings["port"]=port
    if obj.protocol in ("FTP","SSH","MYSQL","SMTP"):
        if not str(settings.get("username","")).strip():
            raise ValueError("Username required")
    if obj.protocol=="SSH":
        key=str(settings.get("identity","")).strip()
        if not key:raise ValueError("SSH key reference required")
        settings["identity"]=str(Path(key).expanduser())
    if obj.protocol=="FTP":
        if settings.get("mode","FTPS") not in ("FTPS","FTP"):
            raise ValueError("Choose FTPS or FTP")
    if obj.protocol=="SMTP":
        if settings.get("tls","SSL") not in ("SSL","STARTTLS"):
            raise ValueError("SMTP requires SSL or STARTTLS")
    if obj.protocol=="MYSQL":
        if settings.get("tls","required") not in ("required","verify_identity"):
            raise ValueError("MySQL TLS required")
        if not str(settings.get("database","")).strip():
            raise ValueError("MySQL database required")
    timeout=int(settings.get("timeout",7))
    settings["timeout"]=min(20,max(2,timeout))
    if not re.fullmatch("[a-f0-9]{32}",obj.connection_id):
        raise ValueError("Invalid connection ID")
    return ConnectionDefinition(obj.connection_id,obj.name.strip(),obj.protocol,settings)

class UserConnectionRegistry:
    def __init__(self,identity=None,path=None):
        self.identity=identity or MachineIdentity.current()
        if path is None:
            self.suite=SuiteProfileStore(uid=self.identity.uid,username=self.identity.username)
            self.path=self.suite.connections_path
            self._migrate_from=xdg_config()/"connections-v2.json"
        else:
            self.suite=None
            self.path=Path(path)
            self._migrate_from=None
    def _migrate_once(self):
        """Import existing v2 metadata atomically; never discard legacy copy."""
        if (self._migrate_from is None or self.path.exists()
                or not self._migrate_from.is_file()):
            return
        legacy=self._migrate_from
        if legacy.is_symlink() or legacy.stat().st_mode & 0o077:
            return
        try:
            obj=json.loads(legacy.read_text(encoding="utf-8"))
            if obj.get("owner_uid")!=self.identity.uid or obj.get("schema")!=1:
                return
            rows=[]
            for entry in obj.get("connections",[]):
                rows.append(normalize(ConnectionDefinition(**entry)))
            self.save(rows)
        except (OSError,ValueError,TypeError,KeyError):
            return

    def list(self):
        self._migrate_once()
        try:
            data=json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("schema")!=1 or data.get("owner_uid")!=self.identity.uid:
                return []
            entries=data.get("connections",[])
            if not isinstance(entries,list):return []
            out=[]
            for entry in entries[:200]:
                try:
                    out.append(normalize(ConnectionDefinition(
                        entry["connection_id"],entry["name"],entry["protocol"],entry["options"])))
                except (KeyError,TypeError,ValueError):
                    continue
            return out
        except (OSError,ValueError,TypeError):
            return []
    def save(self,records):
        clean=[normalize(x) for x in records]
        if len(clean)>200:raise ValueError("Too many connections")
        if len({x.connection_id for x in clean})!=len(clean):
            raise ValueError("Duplicate IDs")
        directory=self.path.parent
        directory.mkdir(mode=0o700,parents=True,exist_ok=True)
        os.chmod(directory,0o700)
        payload={"schema":1,"owner_uid":self.identity.uid,
                 "connections":[asdict(x) for x in clean]}
        fd,temp=tempfile.mkstemp(prefix=".connections-",suffix=".tmp",dir=directory)
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as stream:
                os.fchmod(stream.fileno(),0o600)
                json.dump(payload,stream,indent=2,ensure_ascii=False)
                stream.flush();os.fsync(stream.fileno())
            os.replace(temp,self.path)
        finally:
            if os.path.exists(temp):os.unlink(temp)
    def upsert(self,record):
        validated=normalize(record)
        old=[x for x in self.list() if x.connection_id!=validated.connection_id]
        self.save(old+[validated])
        return validated
    def remove(self,connection_id):
        existing=self.list()
        filtered=[x for x in existing if x.connection_id!=connection_id]
        self.save(filtered)
        return len(existing)!=len(filtered)

def new_connection(name,protocol,options):
    return normalize(ConnectionDefinition(uuid.uuid4().hex,name,protocol,options))

def readiness(record,secret_available=False):
    """Only proves local prerequisites, never claims remote authentication."""
    p=normalize(record)
    opts=p.options
    if p.protocol=="SQLITE":
        file=Path(opts["path"])
        return ("READY_LOCAL" if file.is_file() and os.access(file,os.R_OK)
                else "MISSING_FILE")
    if p.protocol=="SSH":
        key=Path(opts["identity"]).expanduser()
        if not key.is_file() or not os.access(key,os.R_OK):
            return "MISSING_KEY"
        if key.stat().st_mode & 0o077:
            return "KEY_PERMISSIONS"
        return "READY_TO_TEST"
    if p.protocol in ("MYSQL","SMTP","FTP") and not secret_available:
        return "CREDENTIAL_REQUIRED"
    return "READY_TO_TEST"
