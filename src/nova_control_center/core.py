"""Small event bus and registry. GUI objects stay on the Qt main thread."""
from dataclasses import dataclass
from typing import Callable
from PySide6.QtCore import QObject, Signal

@dataclass(frozen=True)
class AppSpec:
    app_id: str
    label: str
    icon: str
    factory: Callable

class EventBus(QObject):
    event = Signal(str, object)

    def publish(self, name: str, payload: object = None):
        self.event.emit(name, payload)

class AppRegistry:
    def __init__(self):
        self._items: dict[str, AppSpec] = {}

    def register(self, spec: AppSpec):
        if spec.app_id in self._items:
            raise ValueError(f"Duplicate application: {spec.app_id}")
        self._items[spec.app_id] = spec

    def all(self):
        return list(self._items.values())

    def get(self, app_id):
        return self._items[app_id]
