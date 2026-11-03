"""V2.1 checks: no demo apps, custom X11 window chrome, toast/menu and JSON."""
import json
from pathlib import Path
from PySide6.QtCore import Qt
from nova_control_center.nexus_v21 import MainWindow
from nova_control_center.app_registry import discover_manifests, ApplicationRegistry

def test_empty_desktop_and_frameless(qtbot,tmp_path,monkeypatch):
    import nova_control_center.nexus_v21 as module
    monkeypatch.setattr(module,"SETTINGS",tmp_path/"v21.json")
    window=MainWindow()
    qtbot.addWidget(window)
    assert window.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert len(window.desktop.subWindowList())==0
    assert len(window.registry.registered())==0
    assert window.status.height()==31
    window.set_theme("RougeERROR")
    assert window.theme_name=="RougeERROR"
    window.notifications.add("Success","success")
    assert len(window.notifications.toasts)==1
    window.notifications.add("Failure","error")
    assert len(window.notifications.toasts)==2
    window.save_state()
    assert json.loads((tmp_path/"v21.json").read_text())["workspace"]==[]
    window.close()

def test_metadata_discovery_does_not_import_code(tmp_path):
    folder=tmp_path/"some-module"
    folder.mkdir()
    (folder/"manifest.json").write_text('{"id":"nova.test","name":"Module","version":"0.1"}')
    assert len(discover_manifests(tmp_path))==1
    assert not ApplicationRegistry().registered()
