"""NetTrace Mesh: graph validation, multi-VPS testing, authorization and UI tiers."""
from __future__ import annotations
import importlib.util,json
from pathlib import Path
import pytest
APP=Path(__file__).resolve().parents[1]/"N3XV5"/"Applications"/"NexusNetTrace"
spec=importlib.util.spec_from_file_location("mesh",APP/"mesh.py")
mesh=importlib.util.module_from_spec(spec);spec.loader.exec_module(mesh)

def topology():
    return {"schema":1,"nodes":[
        {"id":"client","vps":"Linux client","agent":"local"},
        {"id":"fundamental","vps":"VPS-A","agent":"ssh",
         "ssh_user":"iatbdebug","ssh_host":"vps-a.example.org"},
        {"id":"trading","vps":"VPS-B","agent":"ssh",
         "ssh_user":"iatbdebug","ssh_host":"vps-b.example.org"}],
      "edges":[
        {"id":"client-api","source":"client","target":"fundamental",
         "check":{"command":"probe","url":"https://vps-a.example.org/health"}},
        {"id":"engine-to-engine","source":"fundamental","target":"trading",
         "check":{"command":"tcp","host":"vps-b.example.org","port":8443},
         "remote_enabled":True},
        {"id":"trading-back","source":"trading","target":"fundamental",
         "check":{"command":"tls","host":"vps-a.example.org","port":443},
         "remote_enabled":True}]}

def engines(*args,**kwargs):return {"status":200,"duration_ms":19}
def resolver(host):return {"host":host,"addresses":["203.0.113.1"]}
def port(host,p):return {"open":True,"host":host,"port":p}
def tls(host,p):return {"valid":False,"error":"tls"}

def test_mesh_topology_validation():
    assert len(mesh.validate_topology(topology())["edges"])==3
    bad=topology();bad["edges"][0]["target"]="unknown"
    with pytest.raises(ValueError):mesh.validate_topology(bad)
    bad=topology();bad["nodes"][1]["ssh_host"]="--evil"
    with pytest.raises(ValueError):mesh.validate_topology(bad)
    bad=topology();bad["edges"][0]["check"]["url"]="http://unsafe.example"
    with pytest.raises(ValueError):mesh.validate_topology(bad)

def test_remote_never_runs_without_explicit_authorization():
    seen=[]
    def remote(node,edge):
        seen.append(edge)
        return {"status":200,"duration_ms":24,"Authorization":"must-be-dropped"}
    result=mesh.run_mesh(topology(),engines,resolver,port,tls,
                         allow_remote=False,remote_func=remote)
    assert result["total"]==3 and result["failures"]==2 and not seen
    result=mesh.run_mesh(topology(),engines,resolver,port,tls,
                         allow_remote=True,remote_func=remote)
    assert result["failures"]==0 and seen==["engine-to-engine","trading-back"]
    assert "must-be-dropped" not in json.dumps(result)

def test_ui_shows_faulted_edge_first():
    import sys
    pytest.importorskip("PySide6")
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
    from nova_control_center.nettrace_hud import compact_report
    result=mesh.run_mesh(topology(),engines,resolver,port,tls)
    short=compact_report({"command":"mesh","data":result},(1,2))
    mid=compact_report({"command":"mesh","data":result},(2,3))
    full=compact_report({"command":"mesh","data":result},(4,4))
    assert "2 FAIL" in short["headline"]
    assert len(short["rows"])<len(mid["rows"])<len(full["rows"])
    assert any("engine-to-engin" in str(x) for x in full["rows"])

def test_agent_policy_requires_pinned_root_owned_path(tmp_path):
    policy=tmp_path/"policy.json";policy.write_text(json.dumps(topology()))
    with pytest.raises(PermissionError):
        mesh.agent_once(str(policy),"engine-to-engine",engines,resolver,port,tls)

def test_safe_no_ssh_shell_injection():
    with pytest.raises(ValueError):mesh.remote_edge(
        {"agent":"ssh","ssh_host":"vps.example;touch BAD","ssh_user":"test"},
        "engine-to-engine")
