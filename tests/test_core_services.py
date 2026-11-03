"""NOVA Core preference, SQLite, PIN and GUI smoke tests."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from nova_control_center.core_settings import PreferencesStore, CorePreferences
from nova_control_center.core_logs import LogStore
from nova_control_center.core_sessions import SessionManager
from nova_control_center.nexus_v21 import MainWindow

def test_preferences_versioned_and_private(tmp_path):
    path=tmp_path/"config"/"core.json"
    store=PreferencesStore(path)
    assert store.load().log_retention_days==30
    prefs=CorePreferences(log_retention_days=1000,log_max_records=200)
    store.save(prefs)
    assert store.load().log_retention_days==365
    assert store.load().log_max_records==1000
    assert path.stat().st_mode & 0o077==0

def test_sqlite_logs_filter_redaction_and_retention(tmp_path):
    db=LogStore(tmp_path/"log.sqlite3")
    db.write("INFO","test","startup","Ready",metadata={"api_key":"secret_value","count":3})
    db.write("AUDIT","ssh","connection","authorization=topsecret",session_id="session-1")
    rows=db.recent(limit=10)
    assert len(rows)==2
    assert "topsecret" not in rows[0]["message"]
    assert "secret_value" not in rows[1]["metadata"]
    assert db.recent(level="AUDIT")[0]["source"]=="ssh"
    assert db.recent(contains="Ready")[0]["event"]=="startup"
    with sqlite3.connect(tmp_path/"log.sqlite3") as con:
        assert con.execute("PRAGMA journal_mode").fetchone()[0]=="wal"
    db.prune(days=30,max_rows=1000)
    db.close()

def test_sessions_pin_lock_and_throttle(tmp_path):
    manager=SessionManager(tmp_path/"lock.json")
    assert not manager.lock()
    with pytest.raises(ValueError):manager.set_pin("1234")
    manager.set_pin("123456")
    assert manager.lock()
    assert manager.session.locked
    assert not manager.unlock("000000")
    assert manager.unlock("123456")
    assert not manager.session.locked
    assert (tmp_path/"lock.json").stat().st_mode & 0o077==0
    assert "123456" not in (tmp_path/"lock.json").read_text()

def test_main_core_ui(qtbot,tmp_path,monkeypatch):
    import nova_control_center.nexus_v21 as ui
    import nova_control_center.core_settings as conf
    monkeypatch.setattr(ui,"SETTINGS",tmp_path/"v21.json")
    monkeypatch.setattr(conf,"xdg_config",lambda:tmp_path/"config")
    monkeypatch.setattr(conf,"xdg_data",lambda:tmp_path/"data")
    window=MainWindow()
    qtbot.addWidget(window)
    assert window.log_store.recent(limit=3)[0]["event"]=="session.started"
    assert len(window.registry.registered())==0
    window.bus.publish("nova.test",{"password":"DONT_STORE"})
    rows=window.log_store.recent()
    assert any(r["event"]=="nova.test" for r in rows)
    assert all("DONT_STORE" not in r["message"] for r in rows)
    window.close()
