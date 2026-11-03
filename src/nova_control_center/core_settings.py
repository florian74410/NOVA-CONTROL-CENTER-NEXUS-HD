"""Versioned, atomic NOVA Core preferences (not a credential store)."""
from __future__ import annotations
import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict, fields

def xdg_config():
    return Path(os.environ.get("XDG_CONFIG_HOME",str(Path.home()/".config")))/"nova-control-center"

def xdg_data():
    return Path(os.environ.get("XDG_DATA_HOME",str(Path.home()/".local/share")))/"nova-control-center"

@dataclass
class CorePreferences:
    schema: int=1
    log_retention_days: int=30
    log_max_records: int=100000
    audit_enabled: bool=True
    lock_after_minutes: int=0
    notify_on_errors: bool=True

    def validated(self):
        self.log_retention_days=max(1,min(365,int(self.log_retention_days)))
        self.log_max_records=max(1000,min(1000000,int(self.log_max_records)))
        self.lock_after_minutes=max(0,min(240,int(self.lock_after_minutes)))
        self.audit_enabled=bool(self.audit_enabled)
        self.notify_on_errors=bool(self.notify_on_errors)
        self.schema=1
        return self

class PreferencesStore:
    def __init__(self,path=None):
        self.path=Path(path) if path else xdg_config()/"core.json"

    def load(self):
        try:
            data=json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data,dict):return CorePreferences()
            values={k:data[k] for k in {f.name for f in fields(CorePreferences)} if k in data}
            return CorePreferences(**values).validated()
        except (ValueError,OSError,TypeError):
            return CorePreferences()

    def save(self,settings):
        obj=settings.validated()
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        os.chmod(self.path.parent,0o700)
        temp=self.path.with_suffix(".tmp")
        with temp.open("w",encoding="utf-8") as stream:
            os.chmod(temp,0o600)
            json.dump(asdict(obj),stream,indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp,self.path)
