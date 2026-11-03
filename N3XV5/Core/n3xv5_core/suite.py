"""A platform-aware registry of native applications.

Registry registration does not execute packages or grant authorizations.
Trust verification and real installation are delegated to the installer.
"""
from __future__ import annotations
from .contracts import AppManifest, Platform, validate_manifest

class SuiteRegistry:
    def __init__(self,platform:Platform,ipc_version=1):
        if not isinstance(platform,Platform):raise ValueError("Invalid platform")
        self.platform=platform
        self.ipc_version=ipc_version
        self._apps={}

    def add(self,app):
        app=validate_manifest(app)
        if app.platform!=self.platform:
            raise ValueError("Native package incompatible with this platform")
        if app.ipc_api!=self.ipc_version:
            raise ValueError("Incompatible IPC protocol")
        if app.app_id in self._apps:
            raise ValueError("Duplicate app registration")
        self._apps[app.app_id]=app

    def list(self):
        return tuple(self._apps[k] for k in sorted(self._apps))

    def get(self,app_id):
        return self._apps[app_id]
