"""N3XV5 NetTrace CLI -> authenticated Unix socket -> resizeable 9x9 HUB 2D iFrame."""
from __future__ import annotations
import importlib.util
import json
import socket
import threading
from pathlib import Path
from dataclasses import replace
import pytest
from n3xv5_core.contracts import AppManifest, Platform
from n3xv5_core.profile import SuiteProfile, ProfileGrants
from n3xv5_core.ipc import LocalAppBroker

NETTRACE_PATH=(Path(__file__).resolve().parents[1]/
               "N3XV5/Applications/NexusNetTrace/nettrace.py")
spec=importlib.util.spec_from_file_location("n3xv5_nettrace_hud_cli",NETTRACE_PATH)
nettrace=importlib.util.module_from_spec(spec)
spec.loader.exec_module(nettrace)

def manifest():
    return AppManifest(
        app_id="nexus-nettrace",name="N3XV5 NetTrace",version="0.2.0",
        platform=Platform.LINUX_X64,package_name="n3xv5-nettrace_0.2.0_amd64.deb",
        package_sha256="a"*64,executable="bin/n3xv5-nettrace",ipc_api=1,
        capabilities=("profile.read","connections.read","nettrace.publish"))

@pytest.fixture
def demo():
    return {"command":"probe","data":{
        "target":"https://api.example.test/health?token=[REDACTED]",
        "request_id":"n3xv5-test-001","method":"GET",
        "status":502,"duration_ms":1250,
        "remote_ip":"203.0.113.15",
        "timings_ms":{"namelookup_ms":10,"connect_ms":34,
                      "appconnect_ms":78,"starttransfer_ms":1200,
                      "total_ms":1250},
        "diagnosis":{"issue":"gateway_or_upstream",
                     "advice":"Check upstream health and proxy logs"},
        "response_headers":{"content-type":"application/json",
                            "x-request-id":"n3xv5-test-001"},
        "error":None}}

def test_content_adapts_to_small_medium_large(demo):
    from nova_control_center.nettrace_hud import compact_report
    small=compact_report(demo,(1,2))
    medium=compact_report(demo,(2,3))
    large=compact_report(demo,(4,4))
    assert (small["tier"],medium["tier"],large["tier"])==("small","medium","large")
    assert small["headline"]=="HTTP 502"
    assert len(small["rows"])<len(medium["rows"])<len(large["rows"])
    assert large["hidden"]<=medium["hidden"]<=small["hidden"]
    assert all("PRIVATE" not in str(row) for row in large["rows"])

def test_all_nettrace_commands_render_without_crashing():
    from nova_control_center.nettrace_hud import compact_report
    cases={
        "dns":{"host":"vps.example","addresses":["203.0.113.10"],"duration_ms":6},
        "tcp":{"host":"vps.example","port":443,"open":True,"duration_ms":19},
        "tls":{"host":"vps.example","valid":True,"tls_version":"TLSv1.3",
               "cipher":"TLS_AES_256_GCM_SHA384"},
        "har":{"entries":9,"errors":1,"slowest":[{"status":502,"duration_ms":850,
                                                  "target":"https://test/health"}]},
        "correlate":{"request_id":"n3xv5-test-001",
                     "client":{"status":502},"server_matches":[{"upstream_status":502,
                                                                  "upstream_response_time":"0.8"}]}
    }
    for command,data in cases.items():
        report=compact_report({"command":command,"data":data},(4,4))
        assert report["command"]==command.upper()
        assert report["headline"]
        assert report["rows"]

def test_grid_medium_creation_drag_resize_remove(qtbot,demo):
    from nova_control_center.nettrace_hud import NetTracePanel
    panel=NetTracePanel()
    qtbot.addWidget(panel)
    panel.resize(1000,760)
    panel.show()
    tile=panel.tile
    assert tile is not None
    assert (tile.wcell,tile.hcell)==(2,3)
    assert tile.xcell==0 and tile.ycell==0
    assert panel.apply_report(demo)
    assert tile.resize_cells(4,4)
    assert tile.wcell==4 and tile.hcell==4
    assert tile.resize_cells(1,2)
    assert (tile.wcell,tile.hcell)==(1,2)
    assert not tile.resize_cells(1,1)
    assert panel.grid_view.grid.can_place(0,0,1,2,ignore=tile.key)
    key=tile.key
    panel.grid_view.grid.remove_tile(key)
    assert key not in panel.grid_view.grid.tiles
    assert panel.apply_report(demo)
    assert panel.tile.key!=key
    panel.close()

def test_publish_requires_user_grant_and_registered_app(demo,monkeypatch):
    profile=SuiteProfile.create("NEXUS user")
    events=[]
    broker=LocalAppBroker(lambda:profile,lambda:[],
        event_callback=lambda app,payload:events.append((app,payload)))
    with pytest.raises(PermissionError):
        broker.dispatch(manifest(),"nettrace.publish",demo)
    profile=replace(profile,grants=(ProfileGrants("nexus-nettrace",
                                                  ("nettrace.publish",)),))
    assert broker.dispatch(manifest(),"nettrace.publish",demo)["accepted"]
    assert events[-1]==("nexus-nettrace",demo)
    with pytest.raises(PermissionError):
        broker.dispatch(replace(manifest(),app_id="nexus-other"),"nettrace.publish",demo)
    with pytest.raises(ValueError):
        broker.dispatch(manifest(),"nettrace.publish",{
            "command":"probe","data":{"cookie":"secret"}})
    broker.lock()
    with pytest.raises(PermissionError):
        broker.dispatch(manifest(),"nettrace.publish",demo)

def test_cli_publishes_over_real_unix_socket(demo,monkeypatch):
    profile=SuiteProfile.create("NEXUS user")
    profile=replace(profile,grants=(ProfileGrants("nexus-nettrace",
                                                  ("nettrace.publish",)),))
    events=[]
    broker=LocalAppBroker(lambda:profile,lambda:[],
        event_callback=lambda app,payload:events.append(payload))
    host,client_socket=socket.socketpair()
    broker._sockets["nexus-nettrace"]=host
    class Process:
        def poll(self):return None
    thread=threading.Thread(target=broker._serve,
          args=(manifest(),Process(),host),daemon=True)
    thread.start()
    fd=client_socket.detach()
    monkeypatch.setenv("N3XV5_IPC_FD",str(fd))
    monkeypatch.setenv("N3XV5_APP_ID","nexus-nettrace")
    assert nettrace.publish_to_hub(demo["command"],demo["data"])
    thread.join(timeout=3)
    assert not thread.is_alive()
    assert events==[demo]
    broker.lock()
