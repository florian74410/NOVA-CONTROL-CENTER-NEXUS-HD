#!/usr/bin/env python3
"""NOVA Suite v3 CLI — stdlib bootstrap, atomic per-user wheel deployments.

A new version is installed in its own venv, then the current pointer is
replaced atomically. Never invokes sudo, bash -c, curl | bash or pip as root.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import venv
from pathlib import Path

APP_ID = "nova-control-center"
ENTRY = "nova-control-center"
ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+_-]{0,89}$")
SHA_RE = re.compile(r"^[a-fA-F0-9]{64}$")
CATALOG_NAME = "catalog.json"
MAX_MANIFEST = 512 * 1024
MAX_WHEEL = 400 * 1024 * 1024

def dirs(root=None):
    base = Path(root).expanduser().resolve() if root else (
        Path(os.environ.get("XDG_DATA_HOME", str(Path.home()/".local/share"))) / "nova-suite")
    return base

def ensure_directory(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Installation directory must not be a symlink")
    os.chmod(path, 0o700)

def atomic_json(path, obj):
    ensure_directory(path.parent)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        os.chmod(tmp, 0o600)
        json.dump(obj, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def read_json(path, fallback):
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj,dict) else fallback
    except (OSError,ValueError):
        return fallback

def validate_name(name, regex=ID_RE):
    if not isinstance(name,str) or not regex.fullmatch(name):
        raise ValueError("Invalid package identifier or version")
    return name

def secure_url(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("HTTPS URL without embedded credentials required")
    if parts.hostname.lower() not in ("github.com","raw.githubusercontent.com",
                                       "objects.githubusercontent.com",
                                       "release-assets.githubusercontent.com"):
        raise ValueError("Package source must be an approved GitHub asset host")
    return url

def download(url,target,maximum):
    secure_url(url)
    req=urllib.request.Request(url,headers={"User-Agent":"NOVA-Suite-Installer/3"})
    with urllib.request.urlopen(req,timeout=30) as response:
        if urllib.parse.urlsplit(response.geturl()).scheme != "https":
            raise ValueError("Download redirected outside HTTPS")
        total=0
        with target.open("wb") as stream:
            os.chmod(target,0o600)
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                total+=len(chunk)
                if total>maximum:raise ValueError("Download exceeds safety limit")
                stream.write(chunk)
    return target

def hash_file(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()

def manifest_from(url):
    with tempfile.TemporaryDirectory(prefix="nova-manifest-") as t:
        p=download(url,Path(t)/"manifest.json",MAX_MANIFEST)
        obj=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(obj,dict):raise ValueError("Manifest must be an object")
    return obj

def load_catalog(path):
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    apps=obj.get("apps")
    if obj.get("schema")!=1 or not isinstance(apps,list):
        raise ValueError("Invalid NOVA suite catalog")
    seen=set()
    for app in apps:
        if not isinstance(app,dict):raise ValueError("Invalid application")
        app_id=validate_name(app.get("id"))
        if app_id in seen:raise ValueError("Duplicate application")
        seen.add(app_id)
        validate_name(app.get("entrypoint"))
        if app.get("manifest_url"):secure_url(app["manifest_url"])
    return obj

def catalog_app(catalog,app_id):
    for app in catalog["apps"]:
        if app["id"]==app_id:return app
    raise ValueError("Application not in catalog")

def installed_state(base):
    return read_json(base/"installed.json",{"schema":1,"apps":{}})

def python_venv(path):
    return path/"bin"/"python"

def install(app,version,wheel,sha256,root=None,offline_dir=None,allow_current=False):
    app=validate_name(app)
    version=validate_name(version,VERSION_RE)
    if app!=APP_ID:
        raise ValueError("Only NOVA Control Center is enabled in the current catalog")
    if not SHA_RE.fullmatch(str(sha256)):
        raise ValueError("SHA-256 required for every wheel")
    wheel=Path(wheel).resolve(strict=True)
    if not wheel.is_file() or wheel.suffix!=".whl":
        raise ValueError("Expected a Python .whl distribution")
    if hash_file(wheel).lower()!=sha256.lower():
        raise ValueError("Wheel SHA-256 mismatch; install aborted")
    base=dirs(root)
    ensure_directory(base)
    app_dir=base/"apps"/app
    versions=app_dir/"versions"
    ensure_directory(versions)
    target=versions/version
    current=app_dir/"current"
    if target.exists():
        if not allow_current:raise FileExistsError("Version already installed")
        return target
    with tempfile.TemporaryDirectory(prefix=".staging-",dir=versions) as temp:
        staging=Path(temp)/"environment"
        venv.EnvBuilder(with_pip=True,clear=True,symlinks=True).create(staging)
        cmd=[str(python_venv(staging)),"-m","pip","install","--disable-pip-version-check"]
        if offline_dir:
            cmd.extend(["--no-index","--find-links",str(Path(offline_dir).resolve())])
        cmd.append(str(wheel))
        subprocess.run(cmd,check=True,timeout=900)
        entry=staging/"bin"/ENTRY
        if not entry.is_file():
            raise RuntimeError("Wheel installed, but expected entrypoint missing")
        # Venv has absolute paths: move the whole staging parent to final
        # WITHOUT moving the venv itself after pip generated its entry scripts.
        # This requires stage directory to be at its final path. Instead, create
        # a stable target location before venv construction, remove on failure.
        # NOTE: see stable deployment override below.
        raise RuntimeError("Internal staging path must be stable")

def install_stable(app,version,wheel,sha256,root=None,offline_dir=None):
    """Stable-path venv with atomic pointer switch and rollback on failure."""
    app=validate_name(app)
    version=validate_name(version,VERSION_RE)
    if app!=APP_ID:raise ValueError("Unknown app (not enabled in v3 single-app mode)")
    if not SHA_RE.fullmatch(str(sha256)):raise ValueError("SHA-256 required")
    wheel=Path(wheel).expanduser().resolve(strict=True)
    if not wheel.is_file() or wheel.suffix!=".whl":raise ValueError("Expected .whl")
    if hash_file(wheel).lower()!=sha256.lower():
        raise ValueError("SHA-256 mismatch")
    base=dirs(root)
    ensure_directory(base)
    app_dir=base/"apps"/app
    versions=app_dir/"versions"
    ensure_directory(versions)
    target=versions/version
    current=app_dir/"current"
    if target.exists():raise FileExistsError("Version already exists")
    target.mkdir(mode=0o700)
    try:
        venv.EnvBuilder(with_pip=True,clear=True,symlinks=True).create(target)
        command=[str(python_venv(target)),"-m","pip","install","--disable-pip-version-check"]
        if offline_dir:
            command.extend(["--no-index","--find-links",str(Path(offline_dir).resolve())])
        command.append(str(wheel))
        subprocess.run(command,check=True,timeout=900)
        if not (target/"bin"/ENTRY).is_file():
            raise RuntimeError("Installed wheel does not provide expected launcher")
    except BaseException:
        shutil.rmtree(target,ignore_errors=True)
        raise
    old=None
    if current.is_symlink():
        old=os.readlink(current)
    elif current.exists():
        raise RuntimeError("Unsafe current path: expected symlink")
    link=app_dir/".next"
    link.unlink(missing_ok=True)
    link.symlink_to(target, target_is_directory=True)
    os.replace(link,current)
    state=installed_state(base)
    state["apps"][app]={"version":version,"previous":old,"installed_at":int(time.time())}
    atomic_json(base/"installed.json",state)
    print("Installed:",app,version)
    return target

def rollback(app,root=None):
    app=validate_name(app)
    base=dirs(root)
    state=installed_state(base)
    entry=state["apps"].get(app)
    if not entry or not entry.get("previous"):raise ValueError("No prior version")
    old=Path(entry["previous"])
    versions=(base/"apps"/app/"versions").resolve()
    if old.resolve().parent!=versions or not old.is_dir():
        raise ValueError("Previous installation does not exist")
    current=base/"apps"/app/"current"
    link=current.parent/".next"
    link.unlink(missing_ok=True)
    link.symlink_to(old,target_is_directory=True)
    os.replace(link,current)
    entry["version"]=old.name
    entry["previous"]=None
    atomic_json(base/"installed.json",state)
    print("Restored:",app,old.name)

def register_desktop(base,app=APP_ID):
    """Create local desktop shortcut after app is installed, no root required."""
    bin_dir=Path.home()/".local/bin"
    ensure_directory(bin_dir)
    launcher=base/"launcher.py"
    if not launcher.is_file():raise FileNotFoundError("Missing launcher.py; run bootstrap")
    wrapper=bin_dir/"nova-launcher"
    script="#!/bin/sh\nexec python3 "+__import__("shlex").quote(str(launcher))+" \"$@\"\n"
    wrapper.write_text(script,encoding="utf-8")
    wrapper.chmod(0o700)
    desktop_dir=Path.home()/".local/share/applications"
    desktop_dir.mkdir(parents=True,exist_ok=True)
    desktop=desktop_dir/"nova-control-center.desktop"
    # Desktop file fields are not shell commands. Avoid interpolation from user input.
    desktop.write_text("[Desktop Entry]\nType=Application\n"
                       "Name=NOVA Control Center\nComment=NEXUS HD Suite Launcher\n"
                       "Exec="+str(wrapper)+"\nTerminal=false\n"
                       "Categories=Development;System;\nStartupNotify=true\n",encoding="utf-8")
    desktop.chmod(0o644)
    return desktop

def update(app,manifest_url,root=None):
    doc=manifest_from(manifest_url)
    app=validate_name(app)
    if doc.get("app_id")!=app:raise ValueError("Mismatched app ID")
    version=validate_name(doc.get("version"),VERSION_RE)
    wheel_url=secure_url(doc.get("wheel_url",""))
    digest=doc.get("sha256","")
    if not SHA_RE.fullmatch(str(digest)):raise ValueError("Manifest missing wheel SHA-256")
    state=installed_state(dirs(root))
    if state["apps"].get(app,{}).get("version")==version:
        print("Already up to date:",version)
        return False
    with tempfile.TemporaryDirectory(prefix="nova-package-") as d:
        wheel=Path(d)/urllib.parse.urlsplit(wheel_url).path.rsplit("/",1)[-1]
        if wheel.suffix!=".whl":raise ValueError("Manifest must reference .whl")
        download(wheel_url,wheel,MAX_WHEEL)
        install_stable(app,version,wheel,digest,root)
    return True

def main(argv=None):
    parser=argparse.ArgumentParser(prog="nova-installer",description="NOVA suite CLI v3")
    parser.add_argument("--root",type=Path,default=None,help="Test/portable install root")
    commands=parser.add_subparsers(dest="command",required=True)
    p=commands.add_parser("install",help="Install a locally verified release wheel")
    p.add_argument("--app",default=APP_ID)
    p.add_argument("--version",required=True)
    p.add_argument("--wheel",type=Path,required=True)
    p.add_argument("--sha256",required=True)
    p.add_argument("--offline-dir",type=Path)
    u=commands.add_parser("update",help="Update from approved release manifest")
    u.add_argument("--app",default=APP_ID)
    u.add_argument("--manifest",required=True)
    commands.add_parser("status")
    r=commands.add_parser("rollback")
    r.add_argument("--app",default=APP_ID)
    commands.add_parser("desktop")
    args=parser.parse_args(argv)
    try:
        if args.command=="install":
            install_stable(args.app,args.version,args.wheel,args.sha256,args.root,args.offline_dir)
        elif args.command=="update":
            update(args.app,args.manifest,args.root)
        elif args.command=="rollback":
            rollback(args.app,args.root)
        elif args.command=="desktop":
            print(register_desktop(dirs(args.root)))
        elif args.command=="status":
            print(json.dumps(installed_state(dirs(args.root)),indent=2))
    except (ValueError,OSError,subprocess.SubprocessError,RuntimeError) as exc:
        print("NOVA installer error:",str(exc),file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
