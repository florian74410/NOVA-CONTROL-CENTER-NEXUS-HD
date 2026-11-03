#!/usr/bin/env python3
"""Future NOVA Suite downloader: verified per-app launcher/CLI packages.

One downloader may fetch assets for any number of catalog apps. Does not run
third-party installer source code without an explicit later installation step.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

MAX=20*1024*1024
HOSTS={"github.com","raw.githubusercontent.com","objects.githubusercontent.com",
       "release-assets.githubusercontent.com"}

def catalog(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    apps=data.get("apps")
    if data.get("schema")!=1 or not isinstance(apps,list):raise ValueError("Invalid catalog")
    return apps

def verified_download(url,expected,dest):
    parts=urllib.parse.urlsplit(url)
    if parts.scheme!="https" or parts.hostname not in HOSTS:
        raise ValueError("Unapproved download source")
    if not isinstance(expected,str) or len(expected)!=64:
        raise ValueError("Required SHA-256 is missing")
    int(expected,16)
    digest=hashlib.sha256()
    with urllib.request.urlopen(urllib.request.Request(
            url,headers={"User-Agent":"NOVA-Suite-Downloader/3"}),timeout=25) as response:
        if urllib.parse.urlsplit(response.geturl()).scheme!="https":
            raise ValueError("Insecure redirect")
        count=0
        with dest.open("wb") as file:
            os.chmod(dest,0o600)
            while True:
                chunk=response.read(65536)
                if not chunk:break
                count+=len(chunk)
                if count>MAX:raise ValueError("Downloaded file exceeds 20MB")
                digest.update(chunk)
                file.write(chunk)
    if digest.hexdigest()!=expected.lower():
        dest.unlink(missing_ok=True)
        raise ValueError("Checksum failed")
    return dest

def fetch_app(app,directory):
    name=app.get("id","")
    if not name.replace("-","").isalnum() or "/" in name:
        raise ValueError("Invalid app")
    assets=(("installer_url","installer_sha256","installer.py"),
            ("launcher_url","launcher_sha256","launcher.py"))
    if any(not app.get(url) or not app.get(sha) for url,sha,_ in assets):
        raise ValueError("This application has no published launcher/CLI package yet")
    target=directory/name
    target.mkdir(parents=True,exist_ok=True,mode=0o700)
    try:
        for url,sha,filename in assets:
            verified_download(app[url],app[sha],target/filename)
    except Exception:
        for _,_,filename in assets:(target/filename).unlink(missing_ok=True)
        raise
    return target

def main(argv=None):
    parser=argparse.ArgumentParser(prog="nova-downloader")
    parser.add_argument("--catalog",type=Path,default=Path(__file__).with_name("catalog.json"))
    parser.add_argument("--destination",type=Path,default=Path.home()/"Downloads"/"NOVA-Suite")
    parser.add_argument("action",choices=("list","fetch"))
    parser.add_argument("--app",help="App ID, or 'all'")
    opts=parser.parse_args(argv)
    apps=catalog(opts.catalog)
    if opts.action=="list":
        for a in apps:
            print(a.get("id"),":","published" if a.get("installer_url") else "coming soon")
        return 0
    if not opts.app:parser.error("--app required for fetch")
    selected=apps if opts.app=="all" else [a for a in apps if a.get("id")==opts.app]
    if not selected:parser.error("Unknown application")
    for app in selected:
        print("Fetched:",fetch_app(app,opts.destination))
    return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except (OSError,ValueError,urllib.error.URLError) as exc:
        print("NOVA downloader error:",exc,file=sys.stderr)
        raise SystemExit(1)
