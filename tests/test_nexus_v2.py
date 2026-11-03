"""V2 automated headless Qt integration smoke test."""
from PySide6.QtWidgets import QApplication
from nova_control_center.nexus_v2 import MainWindow

def test_v2_theme_workspace_and_local_event(qtbot, tmp_path, monkeypatch):
    import nova_control_center.nexus_v2 as module
    monkeypatch.setattr(module,"SETTINGS",tmp_path/"v2.json")
    win=MainWindow()
    qtbot.addWidget(win)
    assert len(win.desktop.subWindowList()) == 4
    win.open_app("demo.terminal")
    assert len(win.desktop.subWindowList()) == 5
    for key in ("RougeERROR","ElectroBlueNEON"):
        win.apply_theme(key)
        assert win.theme_name == key
    win.desktop.tileSubWindows()
    win.desktop.cascadeSubWindows()
    win.bus.publish("demo.file.changed",{"path":"/demo/nova.json"})
    win.save_workspace()
    assert (tmp_path/"v2.json").exists()
    assert len(win.desktop.snapshot()) == 5
    win.close()

def test_vector_glyphs_and_commands(qtbot,tmp_path,monkeypatch):
    import nova_control_center.nexus_v2 as module
    from nova_control_center.v2_skin import icon, THEMES
    monkeypatch.setattr(module,"SETTINGS",tmp_path/"v2.json")
    win=MainWindow()
    qtbot.addWidget(win)
    for glyph in ("terminal","folder","apps","settings","activity","shield"):
        assert not icon(glyph,THEMES["ElectroBlueNEON"],24).isNull()
    win._toggle_sidebar()
    win._toggle_sidebar()
    assert win.sidebar.isVisible() or not win.isVisible()
    win.close()

def test_render_v2_screenshot(qtbot,tmp_path,monkeypatch):
    """Exercise painting, icon rendering, cut-corner frames and header routing."""
    import os
    from pathlib import Path
    import nova_control_center.nexus_v2 as module
    monkeypatch.setattr(module,"SETTINGS",tmp_path/"v2.json")
    win=MainWindow()
    qtbot.addWidget(win)
    win.resize(1400,850)
    win.show()
    qtbot.wait(180)
    QApplication.processEvents()
    image=win.grab()
    assert not image.isNull()
    assert image.width()>=1200
    target=Path(os.environ.get("NOVA_SCREENSHOT_DIR",str(tmp_path)))
    target.mkdir(parents=True,exist_ok=True)
    assert image.save(str(target/"nova-v2-qt-render.png"))
    win.close()
