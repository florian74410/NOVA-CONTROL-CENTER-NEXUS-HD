"""NOVA V3 installer/launcher/downloader: pure stdlib, no external network."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

DEPLOY=Path(__file__).resolve().parents[1]/"deploy"
def module(name):
    spec=importlib.util.spec_from_file_location(name,DEPLOY/(name+".py"))
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

def test_catalog_single_app_and_future_extension():
    inst=module("nova_installer")
    catalog=inst.load_catalog(DEPLOY/"catalog.json")
    assert [a["id"] for a in catalog["apps"]]==["nova-control-center"]
    assert catalog["apps"][0]["manifest_url"] is None

def test_hash_and_invalid_update_url(tmp_path):
    inst=module("nova_installer")
    wheel=tmp_path/"some.whl"
    wheel.write_bytes(b"fixture")
    assert inst.hash_file(wheel)==hashlib.sha256(b"fixture").hexdigest()
    try:inst.secure_url("http://github.com/owner/repo/file")
    except ValueError:pass
    else:raise AssertionError("HTTP accepted")
    try:inst.install_stable("nova-control-center","3.0.0",wheel,"0"*64,root=tmp_path/"root")
    except ValueError as exc:assert "SHA-256" in str(exc)
    else:raise AssertionError("Checksum mismatch accepted")
    assert not (tmp_path/"root"/"apps").exists()

def test_bootstrap_local_and_launcher_headless(tmp_path):
    boot=module("bootstrap")
    root=tmp_path/"suite"
    assert boot.main(["--root",str(root),"--no-desktop"])==0
    assert (root/"installer.py").is_file()
    assert (root/"launcher.py").is_file()
    assert (root/"catalog.json").is_file()
    launcher=module("nova_launcher")
    assert launcher.main(["--root",str(root),"--status"])==0
    assert launcher.main(["--root",str(root),"--check"])==0
    assert launcher.entry("nova-control-center",root) is None

def test_downloader_catalog_without_release(tmp_path):
    down=module("nova_downloader")
    apps=down.catalog(DEPLOY/"catalog.json")
    assert down.main(["--catalog",str(DEPLOY/"catalog.json"),"list"])==0
    try:down.fetch_app(apps[0],tmp_path)
    except ValueError as exc:assert "no published" in str(exc)
    else:raise AssertionError("No release was incorrectly downloadable")

def test_install_rollback_preserves_previous(monkeypatch,tmp_path):
    inst=module("nova_installer")
    root=tmp_path/"suite"
    versions=root/"apps"/"nova-control-center"/"versions"
    versions.mkdir(parents=True)
    old=versions/"2.9.0"
    old.mkdir()
    cur=versions.parent/"current"
    cur.symlink_to(old)
    (versions/"3.0.0").mkdir()
    inst.atomic_json(root/"installed.json",{"schema":1,"apps":{
        "nova-control-center":{"version":"3.0.0","previous":str(old)}}})
    inst.rollback("nova-control-center",root)
    assert cur.resolve()==old.resolve()
    assert inst.installed_state(root)["apps"]["nova-control-center"]["version"]=="2.9.0"
