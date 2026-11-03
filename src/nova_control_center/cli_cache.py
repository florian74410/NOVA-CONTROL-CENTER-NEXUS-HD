"""Universal per-CLI data cache and NAME request broker for N3XV5.

The cache has no dependency on IATB-CLI. Any connector exposing request(method,
params) and result(method, data)/failed(method, message) signals can register.
"""
from __future__ import annotations
import time
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal, QTimer

@dataclass
class CacheEntry:
    value: object
    priority: int
    updated_at: float
    status: str = "ok"

class CliCacheManager(QObject):
    updated = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, ttl_seconds=60, parent=None, clock=None):
        super().__init__(parent)
        self.ttl = ttl_seconds
        self.clock = clock or time.monotonic
        self.cache = {}
        self.connectors = {}
        self.pending = {}
        self.wanted = {}
        self.retry = {}
        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._maintenance)
        self._tick.start()

    def register(self, app_id, connector):
        if app_id in self.connectors:
            raise ValueError("CLI already registered: " + app_id)
        self.connectors[app_id] = connector
        self.cache[app_id] = {}
        self.pending[app_id] = set()
        self.wanted[app_id] = set()
        self.retry[app_id] = 0
        connector.result.connect(lambda method, data, app=app_id: self._received(app, method, data))
        connector.failed.connect(lambda method, error, app=app_id: self._failed(app, method, error))

    def unregister(self, app_id):
        self.connectors.pop(app_id, None)
        self.cache.pop(app_id, None)
        self.pending.pop(app_id, None)
        self.wanted.pop(app_id, None)
        self.retry.pop(app_id, None)

    def get(self, app_id, names, force=False):
        if app_id not in self.connectors:
            raise KeyError("Unknown CLI: " + app_id)
        names = list(dict.fromkeys(names))
        self.wanted[app_id].update(names)
        now = self.clock()
        values = self.cache[app_id]
        stale = [name for name in names if force or name not in values or now-values[name].updated_at >= self.ttl]
        if stale:
            self._fetch(app_id, stale)
        return {name: {"value": values[name].value, "priority": values[name].priority,
                       "status": values[name].status,
                       "stale": now-values[name].updated_at >= self.ttl}
                if name in values else {"value": None, "status": "pending", "stale": True}
                for name in names}

    def refresh(self, app_id, names=None):
        return self.get(app_id, names or self.wanted[app_id], force=True)

    def _fetch(self, app_id, names):
        if app_id not in self.connectors or self.pending[app_id]:
            return
        batch = list(dict.fromkeys(names))[:64]
        if not batch:
            return
        self.pending[app_id].update(batch)
        self.connectors[app_id].request("data.get", {"names": batch}, timeout_ms=30000)

    def _received(self, app_id, method, data):
        if app_id not in self.cache or method != "data.get":
            return
        requested = self.pending[app_id]
        self.pending[app_id] = set()
        values = data.get("values", {}) if isinstance(data, dict) else {}
        now = self.clock()
        for name in requested:
            item = values.get(name, {})
            if not isinstance(item, dict) or item.get("status") != "ok":
                continue  # Preserve last valid cache entry.
            self.cache[app_id][name] = CacheEntry(item.get("value"), int(item.get("priority", 1)), now)
        self.retry[app_id] = 0
        self.updated.emit(app_id, self.get(app_id, list(self.wanted[app_id])) if not requested else
                          self._snapshot(app_id))

    def _snapshot(self, app_id):
        now = self.clock()
        return {name: {"value": entry.value, "priority": entry.priority,
                       "status": entry.status, "stale": now-entry.updated_at >= self.ttl}
                for name, entry in self.cache[app_id].items()}

    def _failed(self, app_id, method, error):
        if app_id not in self.pending or method != "data.get":
            return
        self.pending[app_id].clear()
        self.retry[app_id] = self.clock() + 2
        self.failed.emit(app_id, error)

    def _maintenance(self):
        now = self.clock()
        for app_id in list(self.connectors):
            if self.pending[app_id] or now < self.retry[app_id]:
                continue
            stale = [name for name in self.wanted[app_id]
                     if name not in self.cache[app_id] or now-self.cache[app_id][name].updated_at >= self.ttl]
            if stale:
                self._fetch(app_id, stale)
