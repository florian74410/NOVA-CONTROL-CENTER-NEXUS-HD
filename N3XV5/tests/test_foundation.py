"""Pure Python tests of cross-platform N3XV5 application/profile contracts."""
from dataclasses import replace
import pytest
from n3xv5_core import (
 AppManifest,Platform,SuiteRegistry,SuiteProfile,ProfileGrants,
 normalize_platform,validate_manifest
)
from n3xv5_core.contracts import PACKAGING

HASH="a"*64
def app(platform=Platform.LINUX_X64,name="nexus-terminal",package="NEXUS-Terminal.deb"):
    return AppManifest(app_id=name,name="NEXUS Terminal",version="1.0.0",
                       platform=platform,package_name=package,
                       package_sha256=HASH,executable="bin/nexus-terminal",
                       ipc_api=1,capabilities=("connections.read","terminal.execute"))

def test_supported_targets():
    assert normalize_platform("linux","x86_64")==Platform.LINUX_X64
    assert normalize_platform("win32","AMD64")==Platform.WINDOWS_X64
    assert normalize_platform("darwin","arm64")==Platform.MACOS_ARM64
    assert normalize_platform("darwin","x86_64")==Platform.MACOS_X64
    with pytest.raises(ValueError):normalize_platform("linux","arm64")

def test_native_packages_are_not_interchangeable():
    validate_manifest(app())
    for platform,extension in (
        (Platform.WINDOWS_X64,"NEXUS-Terminal.exe"),
        (Platform.MACOS_X64,"NEXUS-Terminal.dmg"),
        (Platform.MACOS_ARM64,"NEXUS-Terminal.dmg"),
        (Platform.LIVE_LINUX_X64,"NEXUS-Terminal.deb")
    ):
        validate_manifest(app(platform,package=extension))
    with pytest.raises(ValueError):
        validate_manifest(app(Platform.WINDOWS_X64,package="NEXUS-Terminal.deb"))
    with pytest.raises(ValueError):
        validate_manifest(app(Platform.MACOS_ARM64,package="NEXUS-Terminal.exe"))
    with pytest.raises(ValueError):
        validate_manifest(replace(app(),package_sha256="unsigned"))

def test_per_platform_registry_no_execution():
    catalog=SuiteRegistry(Platform.LINUX_X64)
    catalog.add(app())
    assert len(catalog.list())==1
    with pytest.raises(ValueError):catalog.add(app())
    with pytest.raises(ValueError):
        catalog.add(app(Platform.WINDOWS_X64,package="NEXUS-Terminal.exe"))

def test_suite_profile_is_not_authentication():
    p=SuiteProfile.create("N3XV5 profile")
    assert not p.permits("nexus-terminal","connections.read")
    assert "password" not in repr(p.export_public()).lower()
    grant=ProfileGrants("nexus-terminal",("connections.read",)).validated()
    p=replace(p,grants=(grant,),connection_ids=("f"*32,)).validated()
    assert p.permits("nexus-terminal","connections.read")
    assert not p.permits("nexus-terminal","terminal.execute")
    with pytest.raises(ValueError):
        replace(p,connection_ids=("f"*32,)*2).validated()
    with pytest.raises(ValueError):
        replace(p,grants=(grant,grant)).validated()
