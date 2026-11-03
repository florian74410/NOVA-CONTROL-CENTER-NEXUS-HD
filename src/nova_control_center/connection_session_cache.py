"""Session-scoped preload of NOVA connection profiles.

Preloading means resolving the current OS user's saved profile descriptors and
local credential availability. It does NOT make network calls or decrypt keys.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from .connection_registry import UserConnectionRegistry, ConnectionDefinition, readiness, PROTOCOLS

@dataclass(frozen=True)
class PreparedConnection:
    profile: ConnectionDefinition
    state: str
    credential_source: str | None = None
    prepared_at: float = 0

class CredentialAvailability:
    """Checks existence of secrets without retrieving secret values into logs."""
    def __init__(self, service="NOVA-Control-Center"):
        self.service=service
    def has_keyring_secret(self,connection_id,kind):
        try:
            import keyring
            return bool(keyring.get_password(self.service+"/"+kind, connection_id))
        except Exception:
            return False
    def ssh_agent_identities(self):
        if not os.environ.get("SSH_AUTH_SOCK") or shutil.which("ssh-add") is None:
            return False
        try:
            result=subprocess.run(["ssh-add","-l"],capture_output=True,
                                  timeout=2,check=False)
            return result.returncode==0
        except (OSError,subprocess.TimeoutExpired):
            return False
    def describe(self,profile):
        proto=profile.protocol
        if proto=="SSH":
            path=Path(profile.options["identity"]).expanduser()
            if path.is_file() and os.access(path,os.R_OK) and not(path.stat().st_mode&0o077):
                return "ssh-key-file"
            if self.ssh_agent_identities():
                return "ssh-agent"
            return None
        if proto in ("FTP","MYSQL","SMTP"):
            return "keyring" if self.has_keyring_secret(profile.connection_id,"password") else None
        if proto=="HTTPS":
            return "keyring" if self.has_keyring_secret(profile.connection_id,"token") else None
        return "not-needed"

class ConnectionSessionCache:
    """Nonsecret connection metadata shared by every application in a NOVA session."""
    def __init__(self, registry=None, credentials=None, event_callback=None):
        self.registry=registry or UserConnectionRegistry()
        self.credentials=credentials or CredentialAvailability()
        self.events=event_callback
        self._entries={}
        self._lock=threading.RLock()
        self._initialized=False
        self._locked=False

    def preload(self):
        """Load local profiles and credential readiness, zero network connections."""
        records=self.registry.list()
        snapshot={}
        for profile in records:
            credential=self.credentials.describe(profile)
            state=readiness(profile, credential in ("keyring","ssh-agent","ssh-key-file"))
            # SSH agent can be used even if the configured identity path is absent,
            # but only after a separate explicit SSH adapter validates host identity.
            if profile.protocol=="SSH" and credential=="ssh-agent" and state=="MISSING_KEY":
                state="AGENT_AVAILABLE"
            snapshot[profile.connection_id]=PreparedConnection(
                profile,state,credential,time.time())
        with self._lock:
            self._entries=snapshot
            self._initialized=True
        if self.events is not None:
            self.events("connections.preloaded",{"count":len(snapshot)})
        return self.list()

    def list(self, protocol=None):
        with self._lock:
            if self._locked:return []
            items=list(self._entries.values())
        if protocol:
            protocol=str(protocol).upper()
            if protocol not in PROTOCOLS:raise ValueError("Unsupported protocol")
            items=[p for p in items if p.profile.protocol==protocol]
        return items

    def get(self, connection_id):
        with self._lock:
            if self._locked:raise PermissionError("NOVA session locked")
            if not self._initialized:raise RuntimeError("NOVA session is not preloaded")
            if connection_id not in self._entries:raise KeyError("Unknown connection")
            return self._entries[connection_id]

    def invalidate(self):
        """Forget prepared connections when user locks or switches sessions."""
        with self._lock:
            self._locked=True
            self._entries={}
            self._initialized=False
        if self.events:self.events("connections.locked",{})

    def unlock_and_reload(self):
        with self._lock:self._locked=False
        return self.preload()

    @property
    def count(self):
        with self._lock:return len(self._entries)

    @property
    def initialized(self):
        with self._lock:return self._initialized and not self._locked
