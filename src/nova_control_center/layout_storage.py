"""Persistent 9x9 workspace layouts; data belongs to CLI cache, not the layout."""
from __future__ import annotations
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from .grid_engine import SIZES, CELLS

DEFAULT_PATH=Path(os.environ.get("XDG_CONFIG_HOME",str(Path.home()/".config")))/"n3xv5"/"grid-layout.json"

def validate_layout(rows):
    if not isinstance(rows,list) or len(rows)>81:raise ValueError("Invalid layout")
    occupied=set();result=[]
    for item in rows:
        if not isinstance(item,dict):raise ValueError("Invalid frame")
        x,y,w,h=(item.get(k) for k in ("x","y","w","h"))
        if any(type(v) is not int for v in (x,y,w,h)) or (w,h) not in SIZES.values() or min(x,y)<0 or x+w>CELLS or y+h>CELLS:
            raise ValueError("Invalid frame geometry")
        cells={(a,b) for a in range(x,x+w) for b in range(y,y+h)}
        if occupied & cells:raise ValueError("Overlapping frames")
        occupied|=cells
        result.append({"title":str(item.get("title",""))[:120],"x":x,"y":y,"w":w,"h":h,
                       "app_id":str(item.get("app_id",""))[:80],"category":str(item.get("category",""))[:80]})
    return result

def save_layout(rows,path=DEFAULT_PATH):
    rows=validate_layout(rows)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with NamedTemporaryFile(mode="w",encoding="utf-8",dir=path.parent,prefix=".grid-",delete=False) as file:
        temp=Path(file.name)
        json.dump({"version":1,"frames":rows},file,ensure_ascii=False,indent=2)
        file.flush();os.fsync(file.fileno())
    os.replace(temp,path)

def load_layout(path=DEFAULT_PATH):
    path=Path(path)
    if not path.exists():return []
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("version")!=1:raise ValueError("Unsupported layout version")
    return validate_layout(data["frames"])
