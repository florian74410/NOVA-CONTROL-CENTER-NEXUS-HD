#!/usr/bin/env python3
"""NOVA bootstrap: install CLI + Launcher files and shortcuts, without sudo.

Run from the extracted, verified NOVA distribution kit.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

def main(argv=None):
    parser=argparse.ArgumentParser(description="Bootstrap NOVA Suite Launcher")
    parser.add_argument("--root",type=Path,help="Optional testing or portable root")
    parser.add_argument("--no-desktop",action="store_true")
    args=parser.parse_args(argv)
    src=Path(__file__).resolve().parent
    dest=args.root.expanduser().resolve() if args.root else (
        Path(os.environ.get("XDG_DATA_HOME",str(Path.home()/".local/share")))/"nova-suite")
    dest.mkdir(mode=0o700,parents=True,exist_ok=True)
    os.chmod(dest,0o700)
    for filename,target in (
        ("nova_installer.py","installer.py"),
        ("nova_launcher.py","launcher.py"),
        ("nova_downloader.py","downloader.py"),
        ("catalog.json","catalog.json")
    ):
        source=src/filename
        if not source.is_file():raise FileNotFoundError(source)
        shutil.copy2(source,dest/target)
        (dest/target).chmod(0o600)
    if not args.no_desktop:
        import importlib.util
        spec=importlib.util.spec_from_file_location("nova_installer",src/"nova_installer.py")
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        path=module.register_desktop(dest)
        print("Desktop shortcut:",path)
    print("NOVA CLI:",dest/"installer.py")
    print("NOVA Launcher:",dest/"launcher.py")
    print("Run: python3",dest/"launcher.py")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
