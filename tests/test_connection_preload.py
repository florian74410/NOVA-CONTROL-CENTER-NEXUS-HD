"""NOVA Core OS-session connection preloading — no remote network calls."""
from pathlib import Path
import json
import os
import pytest
from PySide6.QtWidgets import QApplication
from nova_control_center.connection_registry import (
    MachineIdentity, UserConnectionRegistry, new_connection, readiness, PROTOCOLS
)
from nova_control_center.connection_session_cache import (
    ConnectionSessionCache, CredentialAvailability
)
from nova_control_center.connection_manager_ui import ConnectionManagerDialog
from nova_control_center.nexus_theme import PALETTES
from nova_control_center.nexus_v21 import MainWindow

def fake_identity():
    return MachineIdentity("novauser",1000,"/home/novauser",False)

class FakeCredentials:
    def __init__(self,known=None):self.known=known or {}
    def describe(self,profile):
        return self.known.get(profile.connection_id)

@pytest.fixture
def registry(tmp_path):
    return UserConnectionRegistry(fake_identity(),tmp_path/"profiles.json")

def test_profile_registry_isolation_and_private_storage(registry,tmp_path):
    p=new_connection("API monitor","HTTPS",{"url":"https://example.org/health","method":"HEAD"})
    registry.upsert(p)
    assert registry.path.exists()
    assert registry.path.stat().st_mode & 0o077==0
    assert registry.list()[0].connection_id==p.connection_id
    assert UserConnectionRegistry(MachineIdentity("other",1001,"/tmp",False),
                                  registry.path).list()==[]
    with pytest.raises(ValueError):
        new_connection("bad","HTTPS",{"url":"https://example.org/?token=secret"})
    with pytest.raises(ValueError):
        new_connection("bad","MYSQL",{"host":"localhost","port":3306,
            "username":"u","database":"test","password":"secret"})

def test_preload_all_seven_types(registry,tmp_path):
    key=tmp_path/"id_ed25519"
    key.write_text("test fixture")
    key.chmod(0o600)
    db=tmp_path/"test.sqlite3"
    db.write_bytes(b"fixture")
    samples={
      "FTP":{"host":"localhost","port":21,"username":"ftpuser","mode":"FTPS"},
      "SSH":{"host":"localhost","port":22,"username":"dev","identity":str(key)},
      "HTTPS":{"url":"https://example.org/health"},
      "MYSQL":{"host":"localhost","port":3306,"username":"dbuser","database":"iatb"},
      "SQLITE":{"path":str(db)},
      "SMTP":{"host":"localhost","port":465,"username":"smtpuser"},
      "TCP":{"host":"localhost","port":5222},
    }
    records=[new_connection(p,p,opts) for p,opts in samples.items()]
    registry.save(records)
    cache=ConnectionSessionCache(registry,FakeCredentials({records[0].connection_id:"keyring"}))
    prepared=cache.preload()
    assert len(prepared)==7
    assert set(p.profile.protocol for p in prepared)==set(PROTOCOLS)
    assert cache.list("SSH")[0].state=="READY_TO_TEST"
    assert cache.list("SQLITE")[0].state=="READY_LOCAL"
    assert cache.list("FTP")[0].credential_source=="keyring"
    assert cache.list("SMTP")[0].state=="CREDENTIAL_REQUIRED"
    cache.invalidate()
    assert cache.count==0
    with pytest.raises(PermissionError):cache.get(records[1].connection_id)
    assert len(cache.unlock_and_reload())==7

def test_connection_dialog_and_core_startup(qtbot,registry,tmp_path,monkeypatch):
    import nova_control_center.nexus_v21 as ui
    import nova_control_center.core_settings as conf
    monkeypatch.setattr(ui,"SETTINGS",tmp_path/"v21.json")
    monkeypatch.setattr(conf,"xdg_config",lambda:tmp_path/"conf")
    monkeypatch.setattr(conf,"xdg_data",lambda:tmp_path/"data")
    monkeypatch.setattr(ui,"UserConnectionRegistry",lambda:registry)
    window=MainWindow()
    qtbot.addWidget(window)
    assert window.connection_cache.initialized
    assert window.connection_cache.count==0
    dialog=ConnectionManagerDialog(PALETTES["ElectroBlueNEON"],window.connection_cache,window)
    qtbot.addWidget(dialog)
    assert len(dialog.pages)==7
    dialog.protocol.setCurrentText("HTTPS")
    dialog.name.setText("Main API")
    dialog.pages["HTTPS"].fields["url"].setText("https://example.org/health")
    dialog.save_profile()
    assert window.connection_cache.count==1
    assert len(registry.list())==1
    dialog.close()
    window.close()
