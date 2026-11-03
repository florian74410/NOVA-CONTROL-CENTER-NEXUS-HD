"""N3XV5 N0v4 HUD — suite-wide portable profile contract (v1).

Portable *metadata* lives in the shared suite profile. Credentials do not.
Applications share a profile id and permission grants, not passwords or elevated
OS privileges. Each process verifies the effective OS UID before access.
"""
from __future__ import annotations
import json
import os
import pwd
import re
import tempfile
import uuid
from dataclasses import dataclass,field,asdict
from pathlib import Path

SUITE_ID="n3xv5-n0v4-hud"
SCHEMA=1
APP_ID="nova-control-center"
APP_PATTERN=re.compile(r"^[a-z][a-z0-9-]{2,63}$")
ID_PATTERN=re.compile(r"^[a-f0-9]{32}$")
MAX_APPS=64
MAX_CONNECTIONS=500

def config_root():
    return Path(os.environ.get("XDG_CONFIG_HOME",str(Path.home()/".config")))/SUITE_ID

def effective_identity():
    uid=os.geteuid()
    return uid,pwd.getpwuid(uid).pw_name

def _secure_directory(path):
    path=Path(path)
    path.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.is_symlink():
        raise ValueError("Profile directory cannot be a symlink")
    os.chmod(path,0o700)
    return path

def atomic_write(path,data):
    path=Path(path)
    _secure_directory(path.parent)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=".profile-",suffix=".tmp")
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            os.fchmod(out.fileno(),0o600)
            json.dump(data,out,ensure_ascii=False,sort_keys=True,indent=2)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

@dataclass
class SharedProfile:
    schema:int=SCHEMA
    profile_id:str=""
    label:str=""
    os_uid:int=-1
    os_username:str=""
    app_grants:dict[str,list[str]]=field(default_factory=dict)
    connection_ids:list[str]=field(default_factory=list)

    def validate(self):
        if self.schema!=SCHEMA or not ID_PATTERN.fullmatch(self.profile_id):
            raise ValueError("Invalid suite profile schema/id")
        if not 0<=int(self.os_uid)<2**32 or not self.os_username:
            raise ValueError("Invalid OS identity")
        if len(self.label)>100 or len(self.app_grants)>MAX_APPS:
            raise ValueError("Profile exceeds safe limits")
        if len(self.connection_ids)>MAX_CONNECTIONS:
            raise ValueError("Too many connections")
        if len(set(self.connection_ids))!=len(self.connection_ids):
            raise ValueError("Duplicate connection id")
        if any(not ID_PATTERN.fullmatch(v) for v in self.connection_ids):
            raise ValueError("Invalid connection id")
        for app,grants in self.app_grants.items():
            if not APP_PATTERN.fullmatch(app) or not isinstance(grants,list):
                raise ValueError("Invalid application permission")
            if len(grants)>64 or any(not isinstance(g,str) or len(g)>90 for g in grants):
                raise ValueError("Invalid grant")
        return self

class SuiteProfileStore:
    def __init__(self,root=None,uid=None,username=None):
        actual_uid,actual_name=effective_identity()
        self.uid=actual_uid if uid is None else int(uid)
        self.username=actual_name if username is None else str(username)
        self.root=Path(root) if root else config_root()
        self.profile_path=self.root/"profiles"/str(self.uid)/"active.json"
        self.connections_path=self.root/"profiles"/str(self.uid)/"connections-v2.json"

    def load(self):
        try:
            data=json.loads(self.profile_path.read_text(encoding="utf-8"))
            profile=SharedProfile(**data).validate()
            if profile.os_uid!=self.uid or profile.os_username!=self.username:
                raise ValueError("Wrong operating-system account")
            return profile
        except FileNotFoundError:
            return None

    def ensure(self):
        try:
            profile=self.load()
        except (ValueError,TypeError,KeyError,UnicodeError):
            # Corrupted profiles are NOT silently overwritten.
            raise
        if profile is None:
            profile=SharedProfile(profile_id=uuid.uuid4().hex,
                label=self.username,os_uid=self.uid,os_username=self.username,
                app_grants={APP_ID:["profile.read","connections.read"]})
            self.save(profile)
        return profile

    def save(self,profile):
        profile.validate()
        if profile.os_uid!=self.uid or profile.os_username!=self.username:
            raise PermissionError("Cannot write another local account's profile")
        atomic_write(self.profile_path,asdict(profile))

    def sync_connections(self,connection_ids):
        p=self.ensure()
        ids=list(dict.fromkeys(connection_ids))
        if p.connection_ids!=ids:
            p.connection_ids=ids
            self.save(p)
        return p

    def permission(self,app_id,capability):
        profile=self.ensure()
        return capability in profile.app_grants.get(app_id,[])

    def grant(self,app_id,capabilities):
        if not APP_PATTERN.fullmatch(app_id):
            raise ValueError("Invalid application")
        profile=self.ensure()
        profile.app_grants[app_id]=sorted(set(capabilities))
        self.save(profile)
        return profile

    def export_sanitized(self,destination):
        """Portable metadata export; cannot transfer secrets or impersonate OS UID.

        On import the destination OS user must explicitly rebind identity, and
        reconfigure credentials in that user's keyring/ssh-agent.
        """
        p=self.ensure()
        obj={"schema":SCHEMA,"suite":SUITE_ID,"label":p.label,
             "applications":sorted(p.app_grants),
             "connection_ids":list(p.connection_ids)}
        atomic_write(destination,obj)
        return destination
