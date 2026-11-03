"""N3XV5 local IPC v1: private inherited socketpair per launched application.

No listening network port, shared login token, passwords or CLI arguments.
The HUB owns one end and starts the known native executable with the other.
The peer is that exact child process, not any arbitrary same-user process.

Transport is Unix socketpair for the Linux integration. Native Windows named
pipes and macOS equivalents must be implemented/tested separately.
"""
from __future__ import annotations
import json
import os
import socket
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from .contracts import APP_ID,AppManifest,validate_manifest

MAX_MESSAGE=8192
ALLOWED_METHODS={"hello","profile.info","connections.list","connection.describe","session.ping","nettrace.publish"}
NETTRACE_COMMANDS={"probe","dns","tcp","tls","har","correlate","mesh"}

def encode(message):
    raw=json.dumps(message,separators=(",",":"),ensure_ascii=False).encode("utf-8")+b"\n"
    if len(raw)>MAX_MESSAGE:
        raise ValueError("IPC message too large")
    return raw

def decode(raw):
    if len(raw)>MAX_MESSAGE or not raw.endswith(b"\n"):
        raise ValueError("IPC malformed frame")
    obj=json.loads(raw)
    if not isinstance(obj,dict):
        raise ValueError("IPC expects object")
    return obj

@dataclass(frozen=True)
class AppSession:
    app_id:str
    process_id:int
    profile_id:str
    connected:bool=True

class LocalAppBroker:
    """Process-verified broker; capability permissions checked per request."""
    def __init__(self,profile_provider,connections_provider,event_callback=None):
        self.profile_provider=profile_provider
        self.connections_provider=connections_provider
        self.event_callback=event_callback
        self._processes={}
        self._sockets={}
        self._locked=False
        self._guard=threading.RLock()

    def launch(self,manifest:AppManifest,executable,extra_args=()):
        if os.name!="posix" or not hasattr(socket,"AF_UNIX"):
            raise NotImplementedError("Linux/Unix launch transport only")
        validate_manifest(manifest)
        if self._locked:
            raise PermissionError("HUB locked")
        path=Path(executable).resolve(strict=True)
        if not path.is_file() or not os.access(path,os.X_OK):
            raise ValueError("Installed native executable not available")
        if manifest.app_id in self._processes and self._processes[manifest.app_id].poll() is None:
            raise ValueError("Application already running")
        host,child=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            child.set_inheritable(True)
            env=os.environ.copy()
            env["N3XV5_IPC_FD"]=str(child.fileno())
            env["N3XV5_APP_ID"]=manifest.app_id
            proc=subprocess.Popen([str(path),*extra_args],pass_fds=(child.fileno(),),
                                  close_fds=True,env=env)
        except Exception:
            host.close()
            raise
        finally:
            child.close()
        with self._guard:
            self._processes[manifest.app_id]=proc
            self._sockets[manifest.app_id]=host
        thread=threading.Thread(target=self._serve,args=(manifest,proc,host),
                                name="n3xv5-ipc-"+manifest.app_id,daemon=True)
        thread.start()
        return proc.pid

    def _allowed(self,manifest,permission):
        profile=self.profile_provider()
        if self._locked or profile is None or getattr(profile,"locked",False):
            return False
        # Both app-declared capability AND user/HUB grant are required.
        return permission in manifest.capabilities and profile.permits(manifest.app_id,permission)

    def dispatch(self,manifest,method,params=None):
        if method not in ALLOWED_METHODS:raise PermissionError("Method refused")
        if self._locked:raise PermissionError("HUB locked")
        profile=self.profile_provider()
        if profile is None:raise PermissionError("No active profile")
        if method=="nettrace.publish":
            if manifest.app_id!="nexus-nettrace":
                raise PermissionError("Only NetTrace may publish network diagnostics")
            if not self._allowed(manifest,"nettrace.publish"):
                raise PermissionError("nettrace.publish denied")
            if not isinstance(params,dict) or params.get("command") not in NETTRACE_COMMANDS:
                raise ValueError("Unknown NetTrace diagnostic")
            data=params.get("data")
            if not isinstance(data,dict):
                raise ValueError("NetTrace report must be an object")
            # No raw headers/bodies/cookies. A strict whitelist of operational
            # data is accepted, and the GUI applies its own smaller projection.
            allowed={
                "probe":{"target","request_id","method","status","http_version","remote_ip",
                         "duration_ms","timings_ms","size_download_bytes","tls_verify_result",
                         "response_headers","error","curl_exit_code","diagnosis","engine","tls_version"},
                "dns":{"host","addresses","duration_ms","error","error_code"},
                "tcp":{"host","port","open","duration_ms","error","error_code"},
                "tls":{"host","port","valid","tls_version","cipher","subject","issuer",
                       "not_after","handshake_ms","error","type"},
                "har":{"entries","errors","slowest","failures"},
                "correlate":{"request_id","client","server_matches","hint"},
                "mesh":{"nodes","edges","total","failures"},
            }[params["command"]]
            if set(data)-allowed:
                raise ValueError("Unsupported diagnostic fields")
            if len(encode({"data":data}))>7000:
                raise ValueError("NetTrace report too large")
            if self.event_callback is not None:
                self.event_callback(manifest.app_id,{"command":params["command"],"data":data})
            return {"accepted":True,"command":params["command"]}
        if method=="hello":
            return {"api":1,"app_id":manifest.app_id}
        if method=="session.ping":
            return {"alive":True}
        if method=="profile.info":
            if not self._allowed(manifest,"profile.read"):
                raise PermissionError("profile.read denied")
            return {"profile_id":profile.profile_id,"display_name":profile.display_name}
        if method in ("connections.list","connection.describe"):
            if not self._allowed(manifest,"connections.read"):
                raise PermissionError("connections.read denied")
            connections=self.connections_provider()
            # Only nonsecret connection ID / human-readable label / protocol.
            descriptors=[{"id":c["id"],"label":c["label"],"protocol":c["protocol"]}
                         for c in connections]
            if method=="connections.list":
                return {"connections":descriptors}
            requested=(params or {}).get("id")
            matches=[c for c in descriptors if c["id"]==requested]
            if not matches:raise KeyError("Unknown connection")
            return matches[0]
        raise PermissionError("Unsupported method")

    def _serve(self,manifest,proc,conn):
        try:
            with conn,conn.makefile("rb") as reader:
                # Short-lived CLI may exit after writing its report; drain
                # the socket to EOF even if its process has already exited.
                while not self._locked:
                    raw=reader.readline(MAX_MESSAGE+1)
                    if not raw:break
                    try:
                        request=decode(raw)
                        if request.get("app_id")!=manifest.app_id or request.get("api")!=1:
                            raise PermissionError("Unrecognized application")
                        response={"id":request.get("id"),
                                  "result":self.dispatch(manifest,request.get("method"),request.get("params"))}
                    except (PermissionError,ValueError,KeyError,TypeError) as exc:
                        response={"id":None,"error":str(exc)[:180]}
                    conn.sendall(encode(response))
        except (BrokenPipeError,ConnectionError,OSError):
            pass
        finally:
            with self._guard:
                if self._sockets.get(manifest.app_id) is conn:
                    self._sockets.pop(manifest.app_id,None)

    def lock(self):
        with self._guard:
            self._locked=True
            for conn in self._sockets.values():
                try:conn.shutdown(socket.SHUT_RDWR)
                except OSError:pass
                try:conn.close()
                except OSError:pass
            self._sockets.clear()

    def unlock(self):
        # A previously launched peripheral must establish a new authenticated
        # IPC session; unlocking never automatically trusts previous channels.
        with self._guard:
            self._locked=False

    def stop_all(self):
        self.lock()
        with self._guard:
            for proc in self._processes.values():
                if proc.poll() is None:proc.terminate()
            self._processes.clear()

class PeripheralClient:
    """SDK client uses only the explicitly inherited descriptor."""
    def __init__(self,fd=None):
        fd=int(fd if fd is not None else os.environ["N3XV5_IPC_FD"])
        self.sock=socket.socket(fileno=fd)
        self.app_id=os.environ["N3XV5_APP_ID"]
        self.reader=self.sock.makefile("rb")

    def request(self,method,params=None):
        self.sock.sendall(encode({"api":1,"id":os.urandom(8).hex(),
                                   "app_id":self.app_id,"method":method,"params":params or {}}))
        return decode(self.reader.readline(MAX_MESSAGE+1))

    def close(self):
        self.reader.close()
        self.sock.close()
