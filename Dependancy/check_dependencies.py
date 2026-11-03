#!/usr/bin/env python3
"""Offline audit of NOVA Suite Dependancy. Never accesses network."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CATEGORIES=("Common/Python/wheels","Apps/NOVA-Control-Center/wheels",
            "Build/Linux-x86_64/wheels")
def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def wheels(root):
    return sorted({p for group in CATEGORIES for p in (root/group).glob("*.whl")})

def matches_wheel(filename,name,version):
    # PEP 427: distribution-version-(optional build)-python-abi-platform.whl
    canonical=lambda t:re.sub(r"[-_.]+","_",t).lower()
    chunks=filename[:-4].split("-")
    return len(chunks)>=5 and canonical(chunks[0])==canonical(name) and chunks[1]==version

def verify(root):
    meta=json.loads((root/"catalog.json").read_text(encoding="utf-8"))
    found=wheels(root)
    missing=[]
    for app in meta.get("apps",[]):
        for req in app.get("requires",[]):
            if not any(matches_wheel(p.name,req["name"],req["version"]) for p in found):
                missing.append(req["name"]+"=="+req["version"])
        package=app.get("distribution")
        if package and not (root/app["folder"]/package).is_file():
            missing.append(package)
    hashes=root/"Checksums"/"SHA256SUMS.txt"
    digest_map={}
    if hashes.exists():
        for line in hashes.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():continue
            parts=line.split(None,1)
            if len(parts)==2:digest_map[parts[1].lstrip("*").strip()]=parts[0].lower()
    corrupt=[]
    for path in found:
        rel=path.relative_to(root).as_posix()
        if rel in digest_map and sha256(path)!=digest_map[rel]:
            corrupt.append(rel)
    return found,missing,corrupt

def main(argv=None):
    parser=argparse.ArgumentParser(description="NOVA Dependancy offline checker")
    parser.add_argument("command",choices=("verify","checksums"))
    parser.add_argument("--root",type=Path,default=ROOT)
    args=parser.parse_args(argv)
    root=args.root.resolve()
    files,missing,corrupt=verify(root)
    if args.command=="checksums":
        path=root/"Checksums"/"SHA256SUMS.txt"
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text("".join(
            sha256(p)+"  "+p.relative_to(root).as_posix()+"\n"
            for p in files),encoding="utf-8")
        print("SHA-256 file written:",path)
        return 0
    for p in files:print("FOUND:",p.relative_to(root))
    for requirement in missing:print("MISSING:",requirement)
    for filename in corrupt:print("HASH MISMATCH:",filename)
    if not missing and not corrupt:print("All pinned runtime wheels present")
    return 1 if missing or corrupt else 0

if __name__=="__main__":raise SystemExit(main())
