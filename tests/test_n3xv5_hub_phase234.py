"""Phase 2-4 regression tests: legacy Qt integration, IPC permissions and offline package staging."""
from __future__ import annotations
import hashlib
import json
import os
import socket
from dataclasses import replace
from pathlib import Path
import pytest
from n3xv5_core import AppManifest,Platform,SuiteProfile,ProfileGrants
from n3xv5_core.installer import NativePackageManager
from n3xv5_core.dependencies import DependencyStore,sha256
from n3xv5_core.ipc import LocalAppBroker,encode,decode,MAX_MESSAGE
from nova_control_center.n3xv5_bridge import manifest_from_json,N3XV5Host
from nova_control_center.nexus_v21 import MainWindow

def manifest(pkg,digest,capabilities=("connections.read",)):
    return AppManifest("nexus-test-app","N3XV5 test app","1.0.0",
                       Platform.LINUX_X64,pkg,digest,"bin/nexus-test",
                       1,capabilities)

def test_shared_offline_cache_validates_hash(tmp_path):
    wheel=tmp_path/"dependency.whl"
    wheel.write_bytes(b"package")
    digest=sha256(wheel)
    store=DependencyStore(tmp_path/"shared",Platform.LINUX_X64)
    assert store.ingest(wheel,digest).is_file()
    assert store.available(digest)
    with pytest.raises(ValueError):store.ingest(wheel,"0"*64)
    assert not store.available("0"*64)

def test_native_install_requires_verified_package_and_dependencies(tmp_path):
    pkg=tmp_path/"N3XV5-App.deb"
    pkg.write_bytes(b"local native package fixture")
    digest=sha256(pkg)
    manager=NativePackageManager(tmp_path/"apps",Platform.LINUX_X64)
    m=manifest(pkg.name,digest)
    saved=manager.stage(m,pkg)
    assert saved.is_file()
    assert manager.list()[m.app_id]["state"]=="staged"
    with pytest.raises(ValueError):
        manager.stage(replace(m,package_sha256="f"*64),pkg)
    assert manager.verified_staged_package(m.app_id)==saved
    pkg2=replace(m,dependencies=("a"*64,))
    with pytest.raises(ValueError):
        manager.stage(pkg2,pkg)
    manager.mark_installed(m.app_id)
    assert manager.list()[m.app_id]["state"]=="installed"
    with pytest.raises(ValueError):manager.verified_staged_package(m.app_id)

def test_native_manifest_platform_and_capabilities():
    m=manifest("N3XV5-App.deb","f"*64)
    valid=manifest_from_json({**m.__dict__,"platform":m.platform.value})
    assert valid==m
    with pytest.raises(ValueError):
        manifest_from_json({**m.__dict__,"platform":"windows-x64"})

def test_ipc_refuses_ungranted_capability_and_never_returns_secret():
    granted=SuiteProfile.create("Tester")
    m=manifest("N3XV5-App.deb","f"*64)
    broker=LocalAppBroker(lambda:granted,lambda:[
        {"id":"c"*32,"label":"Prod SSH","protocol":"SSH",
         "password":"never-leak"}])
    with pytest.raises(PermissionError):
        broker.dispatch(m,"connections.list")
    granted=replace(granted,grants=(
        ProfileGrants("nexus-test-app",("connections.read",)),))
    data=broker.dispatch(m,"connections.list")
    assert data=={"connections":[{"id":"c"*32,"label":"Prod SSH","protocol":"SSH"}]}
    assert "never-leak" not in repr(data)
    with pytest.raises(PermissionError):
        broker.dispatch(m,"profile.info")
    with pytest.raises(PermissionError):
        broker.dispatch(m,"internal.admin")
    broker.lock()
    with pytest.raises(PermissionError):
        broker.dispatch(m,"connections.list")
    broker.unlock()
    assert broker.dispatch(m,"connections.list")["connections"]
    assert decode(encode({"hello":"world"}))=={"hello":"world"}
    with pytest.raises(ValueError):encode({"over":"a"*MAX_MESSAGE})

def test_new_hub_keeps_original_qt_shell(qtbot,tmp_path,monkeypatch):
    # No installation, no password material and no remote connection.
    monkeypatch.setenv("XDG_CONFIG_HOME",str(tmp_path/"cfg"))
    monkeypatch.setenv("XDG_DATA_HOME",str(tmp_path/"data"))
    from nova_control_center import nexus_v21
    from nova_control_center import suite_profile
    from nova_control_center import connection_registry
    monkeypatch.setattr(nexus_v21,"SETTINGS",tmp_path/"v21.json")
    monkeypatch.setattr(nexus_v21,"INSTALLED",tmp_path/"installed")
    monkeypatch.setattr(suite_profile,"config_root",lambda:tmp_path/"suite")
    monkeypatch.setattr(connection_registry,"xdg_config",lambda:tmp_path/"legacy")
    window=MainWindow()
    qtbot.addWidget(window)
    assert hasattr(window,"n3xv5")
    assert window.brand.text()=="N3XV5 N0v4 HUD"
    assert window.n3xv5.package_manager.platform==Platform.LINUX_X64
    window.n3xv5.broker.lock()
    window.close()

def test_private_ipc_socket_roundtrip_and_lock():
    import threading
    from n3xv5_core.ipc import LocalAppBroker
    profile=SuiteProfile.create("N3XV5 test")
    profile=replace(profile,grants=(ProfileGrants("nexus-test-app",("connections.read",)),))
    broker=LocalAppBroker(lambda:profile,lambda:[
        {"id":"d"*32,"label":"SSH debug","protocol":"SSH","token":"UNSAFE"}])
    m=manifest("N3XV5-App.deb","f"*64)
    left,right=socket.socketpair()
    class Live:
        def poll(self):return None
    worker=threading.Thread(target=broker._serve,args=(m,Live(),left),daemon=True)
    worker.start()
    right.sendall(encode({"api":1,"id":"1","app_id":m.app_id,
                          "method":"connections.list","params":{}}))
    data=b""
    right.settimeout(3)
    while not data.endswith(b"\n"):
        data+=right.recv(4096)
    response=decode(data)
    assert response["result"]["connections"][0]["label"]=="SSH debug"
    assert "UNSAFE" not in repr(response)
    broker.lock()
    worker.join(timeout=3)
    assert not worker.is_alive()
    right.close()
