"""V2 native Qt UI smoke tests. QT_QPA_PLATFORM=offscreen pytest -q."""
import json
from nova_control_center.nexus_v2 import MainWindow

def test_full_qt_v2(qtbot, tmp_path, monkeypatch):
    import nova_control_center.nexus_v2 as v2
    monkeypatch.setattr(v2, "SETTINGS", tmp_path / "v2.json")
    window=MainWindow()
    qtbot.addWidget(window)
    assert window.top.height()==79
    assert window.status.height()==33
    assert len(window.desktop.subWindowList())==4
    first=window.desktop.subWindowList()[0]
    assert first.width()>=350
    window.desktop.open_app("demo.terminal")
    assert len(window.desktop.subWindowList())==5
    for theme in ("RougeERROR","ElectroBlueNEON"):
        window.set_theme(theme)
        assert window.desktop.palette.key==theme
    window.bus.publish("demo.file.changed",{"path":"/demo/config.json"})
    window.desktop.tileSubWindows()
    window.save_state()
    data=json.loads((tmp_path/"v2.json").read_text())
    assert len(data["workspace"])==5
    window.close()

def test_svg_icon_and_pcb_palette(qtbot):
    from nova_control_center.nexus_v2_paint import vector_icon
    from nova_control_center.nexus_theme import PALETTES
    from PySide6.QtCore import QSize
    icon=vector_icon("folder", PALETTES["ElectroBlueNEON"].bright, 28)
    assert not icon.pixmap(QSize(28,28)).isNull()
