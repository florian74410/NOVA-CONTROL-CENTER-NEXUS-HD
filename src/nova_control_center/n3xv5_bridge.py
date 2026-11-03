"""Linux Desktop adapter for the new shared N3XV5 Core.

Keeps existing Control Center Qt shell, its neon effects and existing profile
registry. No app can gain capabilities merely by declaring a manifest.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from n3xv5_core.contracts import AppManifest,Platform,validate_manifest
from n3xv5_core.profile import SuiteProfile,ProfileGrants
from n3xv5_core.installer import NativePackageManager
from n3xv5_core.ipc import LocalAppBroker

def manifest_from_json(content):
    if isinstance(content,(str,bytes)):
        content=json.loads(content)
    if not isinstance(content,dict):
        raise ValueError("Application manifest must be an object")
    props=("app_id","name","version","platform","package_name",
           "package_sha256","executable","ipc_api")
    if any(prop not in content for prop in props):raise ValueError("Incomplete native application manifest")
    return validate_manifest(AppManifest(
        app_id=content["app_id"],name=content["name"],version=content["version"],
        platform=Platform(content["platform"]),package_name=content["package_name"],
        package_sha256=content["package_sha256"],executable=content["executable"],
        ipc_api=int(content["ipc_api"]),capabilities=tuple(content.get("capabilities",[])),
        dependencies=tuple(content.get("dependencies",[]))))

class N3XV5Host:
    def __init__(self,profile_store,connection_cache,session_manager,root=None,event_callback=None):
        if os.name!="posix":raise NotImplementedError("Qt bridge Linux first")
        self.profile_store=profile_store
        self.connection_cache=connection_cache
        self.session_manager=session_manager
        self.package_manager=NativePackageManager(
            root or Path.home()/".local"/"share"/"n3xv5-n0v4-hud",Platform.LINUX_X64)
        self.broker=LocalAppBroker(self._active_profile,self._connections,
                                   event_callback=event_callback)

    def _active_profile(self):
        if self.session_manager.session.locked:
            return None
        p=self.profile_store.ensure()
        grants=tuple(ProfileGrants(k,tuple(v)) for k,v in p.app_grants.items())
        return SuiteProfile(p.profile_id,p.label or p.os_username,grants,
                            tuple(p.connection_ids)).validated()

    def _connections(self):
        return [{"id":c.profile.connection_id,"label":c.profile.name,
                 "protocol":c.profile.protocol} for c in self.connection_cache.list()]

    def lock(self):self.broker.lock()
    def unlock(self):self.broker.unlock()
    def close(self):self.broker.stop_all()

    def grant(self,app_id,capabilities):
        # Called only after explicit UI authorization. Persist as local account.
        self.profile_store.grant(app_id,capabilities)

    def launch(self,app_id,executable,extra_args=()):
        records=self.package_manager.list()
        if app_id not in records:raise KeyError("App is not registered")
        record=records[app_id]
        if record["state"]!="installed":
            raise PermissionError("Install native package through OS first")
        manifest=manifest_from_json(record["manifest"])
        return self.broker.launch(manifest,executable,extra_args=extra_args)
