"""N3XV5 NetTrace Mesh v0.3 — distributed diagnostic of engine-to-engine edges.

Topology is declarative, not a network sniffer or path-tracing oracle. An
edge is tested FROM its source machine by the local CLI or an allowlisted
remote NetTrace agent invoked through a preconfigured SSH account.
Remote agent trusts only its OWN local /etc/n3xv5/nettrace-agent.json and
uses fixed edge IDs; the client cannot supply arbitrary target URLs.
"""
from __future__ import annotations
import ipaddress
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit

NODE_ID=re.compile(r"^[a-z][a-z0-9_-]{1,39}$")
MAX_EDGES=128
MAX_NODES=64
MAX_BYTES=256*1024
MAX_AGENT_REPLY=32*1024
AGENT_CONFIG="/etc/n3xv5/nettrace-agent.json"
ALLOWED=("probe","dns","tcp","tls")
def _id(text):
    if not isinstance(text,str) or not NODE_ID.fullmatch(text):
        raise ValueError("Invalid engine/node/edge id")
    return text

def _host(host):
    if not isinstance(host,str) or not host or len(host)>253 or any(ch.isspace() for ch in host):
        raise ValueError("Invalid hostname")
    if host.startswith("-") or any(ch in host for ch in ("@","/","\\",":",";","|","$","'","\"")):
        raise ValueError("Invalid SSH hostname")
    return host

def _endpoint(spec):
    if not isinstance(spec,dict):
        raise ValueError("Endpoint is not an object")
    typ=spec.get("command")
    if typ not in ALLOWED:
        raise ValueError("Unsupported diagnostic protocol")
    if typ=="probe":
        url=spec.get("url","")
        from urllib.parse import urlsplit
        parts=urlsplit(url)
        if parts.scheme!="https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("Mesh HTTP probes must use HTTPS without credentials")
        if parts.query or parts.fragment:
            raise ValueError("Mesh health URLs must not contain query values/fragments")
        if len(url)>1024:
            raise ValueError("Mesh target URL too long")
        return {"command":typ,"url":url}
    host=spec.get("host")
    if not isinstance(host,str) or not host or len(host)>253 or any(c in host for c in ("/","\\","@"," ")):
        raise ValueError("Invalid engine host")
    port=spec.get("port",443)
    if not isinstance(port,int) or not 1<=port<=65535:
        raise ValueError("Invalid port")
    return {"command":typ,"host":host,"port":port}

def validate_topology(data):
    if not isinstance(data,dict) or data.get("schema")!=1:
        raise ValueError("Unsupported mesh topology schema")
    nodes=data.get("nodes")
    edges=data.get("edges")
    if not isinstance(nodes,list) or not isinstance(edges,list) or len(nodes)>MAX_NODES or len(edges)>MAX_EDGES:
        raise ValueError("Invalid mesh sizes")
    by_id={}
    for node in nodes:
        if not isinstance(node,dict):
            raise ValueError("Invalid node")
        node_id=_id(node.get("id"))
        if node_id in by_id:raise ValueError("Duplicate node")
        if not isinstance(node.get("vps"),str) or len(node["vps"])>100:
            raise ValueError("Invalid VPS label")
        agent=node.get("agent","local")
        if agent not in ("local","ssh"):
            raise ValueError("Invalid agent type")
        if agent=="ssh":
            _host(node.get("ssh_host"))
            user=node.get("ssh_user")
            if not isinstance(user,str) or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}",user):
                raise ValueError("Invalid SSH account")
        by_id[node_id]=node
    found=set()
    for edge in edges:
        if not isinstance(edge,dict):raise ValueError("Invalid edge")
        edge_id=_id(edge.get("id"))
        if edge_id in found:raise ValueError("Duplicate edge")
        found.add(edge_id)
        if edge.get("source") not in by_id or edge.get("target") not in by_id:
            raise ValueError("Unknown endpoint node")
        _endpoint(edge.get("check"))
    return data

def load_config(path):
    p=Path(path).expanduser()
    if not p.is_file() or p.stat().st_size>MAX_BYTES:
        raise ValueError("Topology config missing or too large")
    return validate_topology(json.loads(p.read_text(encoding="utf-8")))

def inspect_link(edge,probe_func,dns_func,tcp_func,tls_func):
    spec=_endpoint(edge["check"])
    kind=spec["command"]
    if kind=="probe":
        return probe_func(spec["url"],timeout=12)
    if kind=="dns":
        return dns_func(spec["host"])
    if kind=="tcp":
        return tcp_func(spec["host"],spec["port"])
    return tls_func(spec["host"],spec["port"])

def _redacted(result):
    """Only allow diagnostic fields, never response bodies/cookies/env."""
    allowed={"target","request_id","method","status","duration_ms",
             "timings_ms","remote_ip","response_headers","diagnosis","error",
             "tls_version","tls_verify_result","engine","host","addresses",
             "port","open","valid","cipher","not_after","handshake_ms","http_version"}
    if not isinstance(result,dict):raise ValueError("Malformed agent result")
    return {key:value for key,value in result.items() if key in allowed}

def remote_edge(node,edge_id,ssh_bin="ssh"):
    _id(edge_id)
    if node.get("agent")!="ssh":raise ValueError("Source is not remote")
    host=_host(node["ssh_host"])
    user=node["ssh_user"]
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}",user):
        raise ValueError("Invalid remote user")
    if not shutil.which(ssh_bin):raise RuntimeError("SSH client unavailable")
    command=[ssh_bin,"-T","-o","BatchMode=yes",
             "-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=8",
             "--",f"{user}@{host}","n3xv5-nettrace","mesh-agent",
             "--config",AGENT_CONFIG]
    # No shell construction and no arbitrary remote commands.
    proc=subprocess.run(command,input=(json.dumps({"edge_id":edge_id})+"\n").encode(),
                        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                        check=False,timeout=25)
    if proc.returncode:
        raise RuntimeError("Remote NetTrace agent unavailable or refused request")
    if len(proc.stdout)>MAX_AGENT_REPLY:
        raise ValueError("Agent response too large")
    response=json.loads(proc.stdout)
    if response.get("edge_id")!=edge_id or not isinstance(response.get("data"),dict):
        raise ValueError("Agent returned wrong edge")
    return _redacted(response["data"])

def agent_once(config_path,edge_id,probe_func,dns_func,tcp_func,tls_func):
    """Remote-side authorization uses ONLY that VPS's root-administered config."""
    if Path(config_path).resolve()!=Path(AGENT_CONFIG):
        raise PermissionError("Remote agent config must be the pinned system policy file")
    policy_file=Path(config_path)
    if policy_file.is_symlink():
        raise PermissionError("Remote agent policy cannot be a symlink")
    st=policy_file.stat()
    if st.st_uid!=0 or (st.st_mode & 0o022):
        raise PermissionError("Remote agent policy must be root-owned and not group/world writable")
    policy=load_config(config_path)
    edge=next((item for item in policy["edges"] if item["id"]==edge_id),None)
    if edge is None or not edge.get("remote_enabled",False):
        raise PermissionError("Edge not allowlisted for this remote agent")
    data=inspect_link(edge,probe_func,dns_func,tcp_func,tls_func)
    return {"edge_id":edge_id,"data":_redacted(data)}

def run_mesh(topology,probe_func,dns_func,tcp_func,tls_func,allow_remote=False,remote_func=remote_edge):
    topo=validate_topology(topology)
    nodes={x["id"]:x for x in topo["nodes"]}
    results=[]
    for edge in topo["edges"]:
        source=nodes[edge["source"]]
        begin=time.monotonic()
        try:
            if source.get("agent","local")=="ssh":
                if not allow_remote:
                    raise PermissionError("Remote diagnostic needs explicit --allow-remote")
                data=_redacted(remote_func(source,edge["id"]))
            else:
                data=_redacted(inspect_link(edge,probe_func,dns_func,tcp_func,tls_func))
            status=data.get("status")
            ok=(data.get("error") is None and data.get("open",True) is not False
                and data.get("valid",True) is not False
                and (not isinstance(status,int) or 200<=status<400))
            item={"id":edge["id"],"source":edge["source"],"target":edge["target"],
                  "source_vps":source["vps"],"target_vps":nodes[edge["target"]]["vps"],
                  "command":edge["check"]["command"],"ok":ok,"data":data}
        except (OSError,ValueError,RuntimeError,PermissionError,TimeoutError) as exc:
            item={"id":edge["id"],"source":edge["source"],"target":edge["target"],
                  "source_vps":source["vps"],"target_vps":nodes[edge["target"]]["vps"],
                  "command":edge["check"]["command"],"ok":False,
                  "data":{"error":type(exc).__name__}}
        item["elapsed_ms"]=round((time.monotonic()-begin)*1000,2)
        results.append(item)
    return {"nodes":[{"id":n["id"],"vps":n["vps"]} for n in topo["nodes"]],
            "edges":results,"total":len(results),
            "failures":sum(not e["ok"] for e in results)}
