"""NOVA registry — installed Qt application metadata; no demo applications.

Deliberately does not execute untrusted Python modules on discovery.
A future installer must explicitly authorize a module and bind its factory.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from PySide6.QtWidgets import QWidget

@dataclass(frozen=True)
class ApplicationDescriptor:
    app_id: str
    title: str
    icon: str
    factory: Callable
    minimum: tuple[int, int] = (350, 230)

class ApplicationRegistry:
    def __init__(self):
        self._items: dict[str, ApplicationDescriptor] = {}
    def register(self, item: ApplicationDescriptor):
        if item.app_id in self._items:
            raise ValueError("Application already registered: " + item.app_id)
        self._items[item.app_id] = item
    def registered(self):
        return list(self._items.values())
    def descriptors(self):
        return list(self._items.values())
    def get(self, app_id):
        return self._items[app_id]

def discover_manifests(directory: Path) -> list[dict]:
    """Display metadata of installed packages, without importing/executing code."""
    records=[]
    for file in sorted(directory.glob("*/manifest.json")) if directory.is_dir() else []:
        try:
            obj=json.loads(file.read_text(encoding="utf-8"))
            if not isinstance(obj,dict): continue
            if not all(isinstance(obj.get(k),str) and obj[k].strip()
                       for k in ("id","name","version")): continue
            records.append({"id":obj["id"],"name":obj["name"],
                            "version":obj["version"],"status":"not activated"})
        except (OSError,ValueError,UnicodeError):
            continue
    return records
