"""N3XV5 suite profiles and ISO staging: offline/no-privilege tests."""
from __future__ import annotations
import importlib.util
import json
import os
import pathlib
import pytest
from nova_control_center.suite_profile import SharedProfile,SuiteProfileStore,SUITE_ID
from nova_control_center.connection_registry import UserConnectionRegistry,new_connection,MachineIdentity

def test_shared_profile_persists_grants_and_connection_ids(tmp_path):
    store=SuiteProfileStore(root=tmp_path,uid=1000,username="nova")
    profile=store.ensure()
    assert profile.profile_id
    assert store.permission("nova-control-center","connections.read")
    con_id="a"*32
    profile=store.sync_connections([con_id])
    assert profile.connection_ids==[con_id]
    store.grant("nova-terminal",["connections.read","terminal.execute"])
    again=SuiteProfileStore(root=tmp_path,uid=1000,username="nova")
    assert again.load().profile_id==profile.profile_id
    assert again.permission("nova-terminal","terminal.execute")
    assert not again.permission("unknown-app","terminal.execute")
    assert (tmp_path/"profiles"/"1000"/"active.json").stat().st_mode&0o077==0
    text=(tmp_path/"profiles"/"1000"/"active.json").read_text()
    assert "password" not in text.lower()

def test_profile_os_identity_isolation(tmp_path):
    store=SuiteProfileStore(root=tmp_path,uid=1000,username="nova")
    profile=store.ensure()
    with pytest.raises(PermissionError):
        SuiteProfileStore(root=tmp_path,uid=1001,username="other").save(profile)

def test_shared_registry_imports_legacy(tmp_path,monkeypatch):
    import nova_control_center.connection_registry as mod
    from nova_control_center import suite_profile
    identity=MachineIdentity("nova",1000,str(tmp_path),False)
    monkeypatch.setattr(suite_profile,"config_root",lambda:tmp_path/"suite")
    monkeypatch.setattr(mod,"xdg_config",lambda:tmp_path/"legacy")
    legacy=tmp_path/"legacy"/"connections-v2.json"
    legacy.parent.mkdir()
    old=new_connection("Live API","HTTPS",{"url":"https://example.org/health"})
    from dataclasses import asdict
    legacy.write_text(json.dumps({"schema":1,"owner_uid":1000,"connections":[asdict(old)]}))
    legacy.chmod(0o600)
    registry=UserConnectionRegistry(identity)
    assert len(registry.list())==1
    assert registry.path.is_file()
    assert legacy.is_file()

def load_iso_module():
    p=pathlib.Path(__file__).resolve().parents[1]/"deploy"/"live_iso"/"build_live_iso.py"
    spec=importlib.util.spec_from_file_location("live_iso_builder",p)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_iso_stage_avoids_private_files(tmp_path):
    iso=load_iso_module()
    pkg=tmp_path/"NOVA-Control-Center_2.4.1-dev0_amd64.deb"
    pkg.write_bytes(b"fixture")
    src=tmp_path/"Dependancy"
    src.mkdir()
    (src/"keep.whl").write_bytes(b"wheel")
    (src/"id_ed25519").write_bytes(b"PRIVATE")
    dest=tmp_path/"stage"
    iso.stage(dest,pkg,src)
    assert (dest/"config"/"packages.chroot"/pkg.name).is_file()
    assert (dest/"config"/"package-lists"/"n3xv5-minimal.list.chroot").is_file()
    dep=dest/"config"/"includes.chroot"/"opt"/"n3xv5"/"Dependancy"
    assert (dep/"keep.whl").is_file()
    assert not (dep/"id_ed25519").exists()
    assert (dest/"config"/"includes.chroot"/"usr"/"share"/"xsessions"/"n3xv5.desktop").is_file()
