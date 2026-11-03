"""Native package registration and verified offline staging.

A staged .deb/.exe/.dmg is NOT installed on the host OS. Actual OS package
installation requires an explicit user confirmation and platform installer.
"""
from __future__ import annotations
import json
import os
import shutil
import tempfile
from pathlib import Path
from dataclasses import asdict
from .contracts import AppManifest,Platform,validate_manifest
from .dependencies import DependencyStore,sha256

class NativePackageManager:
    def __init__(self,root,platform:Platform):
        self.root=Path(root)
        self.platform=platform
        self.deps=DependencyStore(self.root/"Dependancy",platform)
        self.catalog=self.root/"packages.json"

    def stage(self,manifest:AppManifest,package_path,dependencies=None):
        validate_manifest(manifest)
        if manifest.platform!=self.platform:
            raise ValueError("Package targets a different OS/architecture")
        source=Path(package_path)
        if not source.is_file() or source.is_symlink() or source.name!=manifest.package_name:
            raise ValueError("Package filename mismatch")
        if sha256(source)!=manifest.package_sha256:
            raise ValueError("Native package failed SHA256 verification")
        # Dependencies are supplied by user as digest-to-local-file mapping.
        inputs=dependencies or {}
        missing=[digest for digest in manifest.dependencies
                 if not self.deps.available(digest) and digest not in inputs]
        if missing:
            raise ValueError("Required offline dependencies missing: "+", ".join(missing))
        for digest,path in inputs.items():
            if digest not in manifest.dependencies:
                raise ValueError("Unrequested dependency")
            self.deps.ingest(path,digest)
        target=self.root/"Packages"/manifest.app_id/manifest.version/manifest.package_name
        target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix=".package-",dir=target.parent)
        try:
            with os.fdopen(fd,"wb") as out,source.open("rb") as stream:
                shutil.copyfileobj(stream,out,1024*1024)
            if sha256(tmp)!=manifest.package_sha256:
                raise ValueError("Package mutated during copy")
            os.replace(tmp,target)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        records=self.list()
        records[manifest.app_id]={"manifest":{
            **asdict(manifest),"platform":manifest.platform.value},
            "package_path":str(target),"state":"staged"}
        self._write_catalog(records)
        return target

    def _write_catalog(self,records):
        self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        fd,tmp=tempfile.mkstemp(prefix=".packages-",dir=self.root)
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as f:
                os.fchmod(f.fileno(),0o600)
                json.dump(records,f,indent=2,sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp,self.catalog)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def list(self):
        if not self.catalog.is_file():return {}
        obj=json.loads(self.catalog.read_text(encoding="utf-8"))
        if not isinstance(obj,dict):raise ValueError("Package registry corrupted")
        return obj

    def verified_staged_package(self,app_id):
        entry=self.list()[app_id]
        manifest=entry["manifest"]
        if entry["state"]!="staged":raise ValueError("Package is not staged")
        path=Path(entry["package_path"]).resolve(strict=True)
        if not path.is_relative_to(self.root.resolve()):
            raise PermissionError("Package path escaped managed directory")
        if sha256(path)!=manifest["package_sha256"]:
            raise ValueError("Staged package integrity failure")
        return path

    def mark_installed(self,app_id):
        """Called only after the native OS installer exits with code zero."""
        entries=self.list()
        path=self.verified_staged_package(app_id)
        entries[app_id]["state"]="installed"
        self._write_catalog(entries)
        return path
