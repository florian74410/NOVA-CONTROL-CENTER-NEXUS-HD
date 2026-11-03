"""GUI smoke tests. Run with QT_QPA_PLATFORM=offscreen pytest -q."""
from PySide6.QtWidgets import QApplication
from nova_control_center.nexus_v1 import MainWindow
from nova_control_center.nexus_theme import PALETTES

def test_multi_window_theme_and_events(qtbot, tmp_path, monkeypatch):
    import nova_control_center.nexus_v1 as module
    monkeypatch.setattr(module, "SETTINGS_FILE", tmp_path / "workspace.json")
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.desktop.subWindowList()
    before = len(window.desktop.subWindowList())
    window.desktop.open_app("demo.terminal")
    assert len(window.desktop.subWindowList()) == before + 1
    for theme in PALETTES:
        window.set_theme(theme)
        assert window.theme_name == theme
    window.bus.publish("demo.file.changed", {"path": "/demo/nova.json"})
    window.save_state()
    assert (tmp_path / "workspace.json").exists()
    window.close()
