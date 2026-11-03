"""Tests for NOVA host settings and sessions, no external SSH/API calls."""
from pathlib import Path
import json
import pytest
from PySide6.QtCore import Qt
from nova_control_center.control_panels import (
    ControlSettingsDialog,ControlSessionsDialog,validated_ssh,load_profiles,save_profiles
)
from nova_control_center.nexus_theme import PALETTES
from nova_control_center.nexus_v21 import MainWindow

def test_host_panels(qtbot,tmp_path,monkeypatch):
    import nova_control_center.control_panels as cp
    import nova_control_center.nexus_v21 as ui
    monkeypatch.setattr(cp,"PROFILE_PATH",tmp_path/"connections.json")
    monkeypatch.setattr(cp,"PROFILE_DIR",tmp_path)
    monkeypatch.setattr(ui,"SETTINGS",tmp_path/"v21.json")
    window=MainWindow()
    qtbot.addWidget(window)
    settings=ControlSettingsDialog(PALETTES["ElectroBlueNEON"],window)
    qtbot.addWidget(settings)
    assert settings.windowFlags() & Qt.WindowType.FramelessWindowHint
    settings.opacity.setValue(74)
    settings.sidebar.setValue(240)
    settings.applied.connect(window.apply_settings)
    settings.save()
    assert window.splitter.sizes()[0]>=160
    sessions=ControlSessionsDialog(PALETTES["ElectroBlueNEON"],window)
    qtbot.addWidget(sessions)
    assert sessions.api_url is not None
    assert sessions.ssh_list.count()==0
    sessions.close()
    window.close()

def test_ssh_profile_validation(tmp_path):
    key=tmp_path/"identity"
    key.write_text("fixture")
    key.chmod(0o600)
    data={"name":"GEN-1","host":"example.org","user":"ubuntu",
          "port":22,"identity":str(key)}
    args=validated_ssh(data)
    assert args[0]=="ssh"
    assert "StrictHostKeyChecking=yes" in args
    data["host"]="test;id"
    with pytest.raises(ValueError):validated_ssh(data)
