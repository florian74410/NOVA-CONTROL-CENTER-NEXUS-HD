"""Local application lock and session lifecycle.

Local PIN is an optional convenience lock, not OS-level security. Credentials
stay with ssh-agent / the system keyring, never in the session SQLite log.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from dataclasses import dataclass
from .core_settings import xdg_config

@dataclass
class Session:
    session_id: str
    started: float
    last_activity: float
    locked: bool=False
    active_connection_id: str|None=None

class SessionManager:
    def __init__(self,credential_file=None):
        self.credential_file=Path(credential_file) if credential_file else xdg_config()/"lock.json"
        self.session=Session(secrets.token_hex(12),time.time(),time.monotonic())
        self.failures=0
        self.next_attempt=0.0

    def has_pin(self):
        return self.credential_file.is_file()

    def set_pin(self,pin):
        if not isinstance(pin,str) or not pin.isdigit() or not 6<=len(pin)<=16:
            raise ValueError("PIN numérique de 6 à 16 chiffres requis")
        salt=secrets.token_bytes(16)
        digest=hashlib.scrypt(pin.encode(),salt=salt,n=2**14,r=8,p=1,dklen=32)
        data={"version":1,"salt":base64.b64encode(salt).decode(),
              "hash":base64.b64encode(digest).decode()}
        self.credential_file.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        os.chmod(self.credential_file.parent,0o700)
        temporary=self.credential_file.with_suffix(".tmp")
        with temporary.open("w",encoding="utf-8") as stream:
            os.chmod(temporary,0o600)
            json.dump(data,stream)
        os.replace(temporary,self.credential_file)

    def unlock(self,pin):
        if not self.has_pin():
            return False
        if time.monotonic()<self.next_attempt:
            return False
        try:
            data=json.loads(self.credential_file.read_text(encoding="utf-8"))
            salt=base64.b64decode(data["salt"],validate=True)
            expected=base64.b64decode(data["hash"],validate=True)
            digest=hashlib.scrypt(str(pin).encode(),salt=salt,n=2**14,r=8,p=1,dklen=32)
            ok=hmac.compare_digest(digest,expected)
        except (OSError,ValueError,KeyError,TypeError):
            ok=False
        if ok:
            self.session.locked=False
            self.session.last_activity=time.monotonic()
            self.failures=0
            self.next_attempt=0.0
            return True
        self.failures+=1
        if self.failures>=5:
            self.next_attempt=time.monotonic()+min(120,2**min(7,self.failures-4))
        return False

    def lock(self):
        if not self.has_pin():return False
        self.session.locked=True
        self.session.active_connection_id=None
        return True

    def touch(self):
        if not self.session.locked:
            self.session.last_activity=time.monotonic()

    def auto_lock_due(self,minutes):
        return self.has_pin() and not self.session.locked and minutes>0 and (
            time.monotonic()-self.session.last_activity>=minutes*60)

    def select_connection(self,connection_id):
        if self.session.locked:raise PermissionError("NOVA is locked")
        self.session.active_connection_id=str(connection_id) if connection_id else None
        self.touch()

    def status(self):
        return {"id":self.session.session_id,
                "locked":self.session.locked,
                "connection":self.session.active_connection_id}
