"""N3XV5 CLI Protocol v1: one JSON request on stdin, one JSON response on stdout.

A peripheral may provide its own GUI when standalone; the HUB never imports it.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass

VERSION=1
MAX_BYTES=1024*1024
ID=re.compile(r"^[a-z][a-z0-9-]{2,63}$")
CATEGORIES=("Vitalité","Actions","Services","Journaux","Réseau")

class ProtocolError(ValueError): pass

def request(app_id, method, params=None, request_id="1"):
    if not isinstance(app_id,str) or not ID.fullmatch(app_id): raise ProtocolError("Invalid app id")
    if not isinstance(method,str) or not re.fullmatch(r"[a-z][a-z0-9_.-]{0,79}",method):
        raise ProtocolError("Invalid method")
    if not isinstance(params or {},dict): raise ProtocolError("Params must be an object")
    return {"n3xv5":VERSION,"id":str(request_id),"app":app_id,"method":method,"params":params or {}}

def encode(message):
    data=(json.dumps(message,ensure_ascii=False,separators=(",",":"))+"\n").encode()
    if len(data)>MAX_BYTES: raise ProtocolError("Message exceeds 1 MiB")
    return data

def decode(data):
    if isinstance(data,str): data=data.encode()
    if len(data)>MAX_BYTES or not data.endswith(b"\n"): raise ProtocolError("Invalid frame")
    try: result=json.loads(data)
    except (ValueError,UnicodeDecodeError) as exc: raise ProtocolError("Invalid JSON") from exc
    if not isinstance(result,dict) or result.get("n3xv5")!=VERSION or not isinstance(result.get("id"),str):
        raise ProtocolError("Invalid protocol envelope")
    return result

def response(req,result=None,error=None):
    if (result is None)==(error is None): raise ProtocolError("Exactly one of result/error required")
    payload={"n3xv5":VERSION,"id":req["id"]}
    if error is not None: payload["error"]={"code":str(error),"message":str(error)}
    else: payload["result"]=result
    return payload

def validate_catalog(result):
    if not isinstance(result,dict) or not isinstance(result.get("categories"),list):
        raise ProtocolError("Catalog must contain categories")
    for category in result["categories"]:
        if not isinstance(category,dict) or not isinstance(category.get("id"),str) or not isinstance(category.get("label"),str):
            raise ProtocolError("Invalid category")
        if not isinstance(category.get("commands"),list): raise ProtocolError("Missing commands")
        for command in category["commands"]:
            if not isinstance(command,dict) or not isinstance(command.get("method"),str):
                raise ProtocolError("Invalid command")
    return result
