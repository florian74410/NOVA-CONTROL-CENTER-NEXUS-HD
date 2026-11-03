"""Contracts for real NEXUS apps and connections (no placeholder instances).

Only explicit in-process trusted Qt factories may be registered. Backend adapters
carry no credentials: they receive opaque connection identifiers and consult the
ConnectionBroker when a request is authorized by the user.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol, Any
from PySide6.QtCore import QObject, Signal

class Capability(str, Enum):
    SFTP_READ = "sftp.read"
    SFTP_WRITE = "sftp.write"
    SSH_COMMAND = "ssh.command"
    HTTP_INSPECT = "http.inspect"
    HTTP_BROWSER = "http.browser"
    METRICS_READ = "metrics.read"
    IATB_CLI = "iatb.cli"

@dataclass(frozen=True)
class AppManifest:
    app_id: str
    title: str
    version: str
    icon: str
    capabilities: frozenset[Capability]
    minimum_size: tuple[int, int] = (350, 240)
    descriptions: dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class Event:
    topic: str
    source: str
    connection_id: str
    resource: str = ""
    payload: dict = field(default_factory=dict)

class HostEvents(QObject):
    published = Signal(object)
    def publish(self, event: Event) -> None:
        if not isinstance(event, Event):
            raise TypeError("Expected a structured NEXUS Event")
        self.published.emit(event)

class ConnectionBroker(Protocol):
    """Host-controlled session APIs; implementation must enforce permissions."""
    def connected(self, connection_id: str) -> bool: ...
    def request(self, connection_id: str, capability: Capability,
                action: str, params: dict) -> Any: ...

class AppFactory(Protocol):
    def __call__(self, connections: ConnectionBroker, events: HostEvents) -> object: ...

class ApplicationHost:
    """Central registry with explicit activation, not dynamic imports from JSON."""
    def __init__(self):
        self.available: dict[str, tuple[AppManifest, AppFactory]] = {}
        self.enabled: set[str] = set()
    def install_trusted(self, manifest: AppManifest, factory: AppFactory):
        if manifest.app_id in self.available:
            raise ValueError(f"Duplicate app id: {manifest.app_id}")
        self.available[manifest.app_id] = (manifest, factory)
    def enable(self, app_id: str):
        if app_id not in self.available:
            raise KeyError("Application not installed or trusted")
        self.enabled.add(app_id)
    def active_descriptors(self):
        return [self.available[k][0] for k in sorted(self.enabled)]
