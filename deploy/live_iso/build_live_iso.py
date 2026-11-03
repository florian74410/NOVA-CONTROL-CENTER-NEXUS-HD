#!/usr/bin/env python3
"""Stage an intentionally minimal N3XV5 N0v4 HUD Linux Live ISO.

Preparing the build tree needs no privileges or network. Running live-build
requires an isolated build machine and downloads Debian OS packages at *build*
time. The resulting ISO operates offline except for optional network services.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

SUITE="N3XV5 N0v4 HUD"
DISTRO="trixie"
PACKAGES=[
    "linux-image-amd64","live-boot","live-config",
    "xserver-xorg-core","xserver-xorg-input-libinput","xserver-xorg-video-all",
    "lightdm","xfce4-session","xfwm4","xfdesktop4","xfce4-panel",
    "xfconf","xfce4-settings","xfce4-terminal","thunar",
    "dbus-user-session","policykit-1","network-manager",
    "iproute2","iputils-ping","openssh-client","ca-certificates",
    "openssl","usbutils","pciutils","udev","udisks2",
    "libegl1","libopengl0","libxkbcommon0","libxcb-cursor0",
    "fonts-dejavu-core","alsa-utils",
]
PRIVATE_NAMES=("id_rsa","id_ed25519","private_key","password","credentials",
               "token","secrets","ssh","profile","lock.json")
def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def package_file(deb):
    path=Path(deb).expanduser().resolve(strict=True)
    if not path.is_file() or not path.name.startswith("NOVA-Control-Center_") or path.suffix!=".deb":
        raise ValueError("Provide a built NOVA-Control-Center_*.deb file")
    return path

def stage(destination,deb,shared=None,expected_sha256=None):
    out=Path(destination).expanduser().resolve()
    pkg=package_file(deb)
    if out==Path("/") or out==pkg.parent:
        raise ValueError("Refusing unsafe build path")
    if expected_sha256 and digest(pkg)!=expected_sha256.lower():
        raise ValueError("DEB hash mismatch")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Build directory must be empty")
    out.mkdir(parents=True,exist_ok=True)
    install=out/"config"/"packages.chroot"
    install.mkdir(parents=True)
    shutil.copy2(pkg,install/pkg.name)
    package_list=out/"config"/"package-lists"/"n3xv5-minimal.list.chroot"
    package_list.parent.mkdir(parents=True)
    package_list.write_text("\n".join(PACKAGES)+"\n",encoding="utf-8")
    include=out/"config"/"includes.chroot"/"opt"/"n3xv5"
    include.mkdir(parents=True)
    if shared:
        src=Path(shared).expanduser().resolve(strict=True)
        if not src.is_dir():raise ValueError("Shared Dependancy must be a folder")
        dst=include/"Dependancy"
        dst.mkdir(parents=True)
        for item in src.rglob("*"):
            rel=item.relative_to(src)
            parts=[p.lower() for p in rel.parts]
            if any(bad in part for part in parts for bad in PRIVATE_NAMES):
                continue
            if item.is_symlink():
                raise ValueError("Symlinks in Dependancy are not allowed")
            if item.is_dir():
                (dst/rel).mkdir(parents=True,exist_ok=True)
            elif item.is_file():
                if item.stat().st_size>1024*1024*1024:
                    raise ValueError("Shared asset exceeds size bound")
                (dst/rel).parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(item,dst/rel)
    shortcuts=out/"config"/"includes.chroot"/"usr"/"share"/"xsessions"
    shortcuts.mkdir(parents=True,exist_ok=True)
    (shortcuts/"n3xv5.desktop").write_text(
        "[Desktop Entry]\nName=N3XV5 N0v4 HUD\n"
        "Comment=NOVA Suite Live Session\nExec=/usr/local/bin/n3xv5-session\n"
        "TryExec=/usr/local/bin/n3xv5-session\nType=Application\n",
        encoding="utf-8")
    starter=out/"config"/"includes.chroot"/"usr"/"local"/"bin"
    starter.mkdir(parents=True,exist_ok=True)
    script=starter/"n3xv5-session"
    script.write_text(
        "#!/bin/sh\n"
        "# Minimal session: xfsettingsd, then NOVA. XFCE terminal remains recovery option.\n"
        "xfsettingsd >/dev/null 2>&1 &\n"
        "xfwm4 --compositor=on >/dev/null 2>&1 &\n"
        "exec /usr/bin/nova-control-center\n",encoding="utf-8")
    script.chmod(0o755)
    branding=include/"manifest.json"
    branding.write_text(json.dumps({"suite":SUITE,"base":DISTRO,
        "apps":["nova-control-center"],"shared_profile_schema":1,
        "offline_start":True,"kind":"live-iso-preview"},indent=2),encoding="utf-8")
    print("Staged N3XV5 Live build tree:",out)
    print("Now use --build on a dedicated Debian live-build host.")
    return out

def build(build_dir):
    directory=Path(build_dir).expanduser().resolve(strict=True)
    if not (directory/"config"/"package-lists"/"n3xv5-minimal.list.chroot").is_file():
        raise ValueError("Missing staged live-build tree")
    if not shutil.which("lb"):
        raise RuntimeError("live-build (lb) is required for ISO compilation")
    # Run live-build only on an isolated build machine: it may require root.
    subprocess.run(["lb","config","--distribution",DISTRO,
                    "--architectures","amd64","--binary-images","iso-hybrid",
                    "--debian-installer","none","--apt-recommends","false",
                    "--bootappend-live","boot=live components"],
                   cwd=directory,check=True,timeout=120)
    subprocess.run(["lb","build"],cwd=directory,check=True,timeout=7200)
    return sorted(str(p) for p in directory.glob("*.iso"))

def main(argv=None):
    parser=argparse.ArgumentParser(prog="n3xv5-live-iso")
    parser.add_argument("command",choices=["stage","build"])
    parser.add_argument("--dest",type=Path,required=True)
    parser.add_argument("--deb",type=Path)
    parser.add_argument("--dependancy",type=Path)
    parser.add_argument("--sha256")
    options=parser.parse_args(argv)
    if options.command=="stage":
        if not options.deb:parser.error("--deb required when staging")
        stage(options.dest,options.deb,options.dependancy,options.sha256)
    else:
        for iso in build(options.dest):print("ISO:",iso)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
