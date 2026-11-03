"""Cross-platform native application manifest format.

Manifests are declarations, never executable code or proof of trust.
Signatures, hashes and process authentication will be enforced by the
installer/IPC transport in a separate workstream.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import re
import sys

APP_ID=re.compile(r"^[a-z][a-z0-9-]{2,63}$")
SEMVER=re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
SHA256=re.compile(r"^[0-9a-f]{64}$")

class Platform(str,Enum):
    WINDOWS_X64="windows-x64"
    LINUX_X64="linux-x64"
    MACOS_X64="macos-x64"
    MACOS_ARM64="macos-arm64"
    LIVE_LINUX_X64="live-linux-x64"

PACKAGING={
    Platform.WINDOWS_X64:(".exe",),
    Platform.LINUX_X64:(".deb",),
    Platform.MACOS_X64:(".dmg",),
    Platform.MACOS_ARM64:(".dmg",),
    Platform.LIVE_LINUX_X64:(".deb",),
}

def normalize_platform(system=None,machine=None):
    import platform
    system=(system or sys.platform).lower()
    machine=(machine or platform.machine()).lower()
    if machine in ("x86_64","amd64","x64"):machine="x64"
    elif machine in ("arm64","aarch64"):machine="arm64"
    if system.startswith("win") and machine=="x64":return Platform.WINDOWS_X64
    if system.startswith("linux") and machine=="x64":return Platform.LINUX_X64
    if system in ("darwin","macos") and machine=="x64":return Platform.MACOS_X64
    if system in ("darwin","macos") and machine=="arm64":return Platform.MACOS_ARM64
    raise ValueError("Unsupported native build platform")

@dataclass(frozen=True)
class AppManifest:
    app_id:str
    name:str
    version:str
    platform:Platform
    package_name:str
    package_sha256:str
    executable:str
    ipc_api:int
    capabilities:tuple[str,...]=()
    dependencies:tuple[str,...]=()

def validate_manifest(app:AppManifest):
    if not isinstance(app,AppManifest):raise TypeError("Invalid manifest object")
    if not APP_ID.fullmatch(app.app_id):raise ValueError("Invalid application id")
    if not app.name or len(app.name)>100:raise ValueError("Invalid application name")
    if not SEMVER.fullmatch(app.version):raise ValueError("Invalid semantic version")
    if not isinstance(app.platform,Platform):raise ValueError("Invalid platform")
    if not any(app.package_name.endswith(suffix) for suffix in PACKAGING[app.platform]):
        raise ValueError("Wrong native package type for target platform")
    if "/" in app.package_name or "\\" in app.package_name or app.package_name.startswith("."):
        raise ValueError("Package basename must be simple")
    if not SHA256.fullmatch(app.package_sha256):
        raise ValueError("Package must have a SHA-256 digest")
    if not app.executable or app.executable.startswith(("/","\\",".")) or ".." in app.executable.split("/"):
        raise ValueError("Executable must be relative to installed application root")
    if app.ipc_api!=1:raise ValueError("Unsupported HUB IPC protocol")
    if len(app.capabilities)>64 or len(app.dependencies)>128:
        raise ValueError("Manifest lists exceed limits")
    for item in (*app.capabilities,*app.dependencies):
        if not isinstance(item,str) or len(item)>90 or not re.fullmatch(r"[a-zA-Z0-9_.:+/-]+",item):
            raise ValueError("Invalid capability or dependency reference")
    for digest in app.dependencies:
        if not SHA256.fullmatch(digest):
            raise ValueError("Offline dependencies must be pinned by SHA-256")
    return app
