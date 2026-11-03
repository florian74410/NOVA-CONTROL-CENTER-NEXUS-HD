"""N3XV5 adapter for the existing IATB-CLI 1.3 FINAL (Linux).

Run as: python -m nova_control_center.iatb_adapter --n3xv5-request
The original 'iatb' executable stays independent and is never modified.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
from n3xv5_core.cli_protocol import decode,encode,response

COMMANDS={
 "vps.status":("Vitalité",["vps","status"],"text"),
 "vps.resources":("Vitalité",["vps","resources"],"text"),
 "vps.ps":("Services",["vps","ps"],"table"),
 "vps.logs.fundamental":("Journaux",["vps","logs","fundamental"],"text"),
 "vps.audit":("Services",["vps","audit"],"text"),
 "vps.benchmark":("Vitalité",["vps","benchmark"],"text"),
 "vps.doctor":("Vitalité",["vps","doctor"],"text"),
 "gen1.status":("Vitalité",["gen1","status"],"text"),
 "gen1.resources":("Vitalité",["gen1","resources"],"text"),
 "gen1.apps.list":("Services",["gen1","apps","list"],"table"),
 "gen1.apps.health":("Services",["gen1","apps","health"],"text"),
 "gen1.caddy.check":("Réseau",["gen1","caddy","check"],"text"),
 "doctor":("Actions",["doctor"],"text"),
 "contabo.instances":("Services",["contabo","instances"],"table"),
 "git.status":("Actions",["git","status"],"text"),
}
# Commands that request confirmation, start Docker, open SSH/tunnels or change
# the VPS state are intentionally not in this read-only first integration.
def catalog():
    categories=[]
    for label in ("Vitalité","Actions","Services","Journaux","Réseau"):
        commands=[{"method":method,"label":" ".join(argv),"kind":kind,"refresh_ms":10000 if label=="Vitalité" else 0}
                  for method,(group,argv,kind) in COMMANDS.items() if group==label]
        categories.append({"id":label.lower(),"label":label,"commands":commands})
    return {"name":"VPS IATB","app":"iatb-cli","categories":categories}

def dispatch(method,params):
    if method=="catalog.describe":return catalog()
    if method not in COMMANDS:raise ValueError("Unknown or unsupported IATB command")
    if params:raise ValueError("This command accepts no parameters")
    program=os.environ.get("N3XV5_IATB_EXECUTABLE") or shutil.which("iatb")
    if not program:raise FileNotFoundError("iatb executable not installed")
    args=COMMANDS[method][1]
    try:
        result=subprocess.run([program,*args],capture_output=True,text=True,
                              errors="replace",timeout=20,check=False)
    except subprocess.TimeoutExpired as exc:raise TimeoutError("IATB command timeout") from exc
    return {"exit_code":result.returncode,"stdout":result.stdout[:65536],
            "stderr":result.stderr[:4096],"argv":args}

def main():
    try:
        raw=sys.stdin.buffer.readline(1024*1024+1)
        req=decode(raw)
        if req.get("app")!="iatb-cli":raise ValueError("Wrong peripheral id")
        result=response(req,result=dispatch(req.get("method"),req.get("params") or {}))
    except Exception as exc:
        req=locals().get("req",{"id":"unknown"})
        result=response(req,error=type(exc).__name__+": "+str(exc))
    sys.stdout.buffer.write(encode(result))
    return 0

if __name__=="__main__":raise SystemExit(main())
