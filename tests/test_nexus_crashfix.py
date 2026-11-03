"""NEXUS QT regression tests: repeated paint, dialogs, updater data validation."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from nova_control_center.nexus_v21_effects import PulseIndicator
from nova_control_center.nexus_theme import PALETTES
from nova_control_center.control_panels import ControlSessionsDialog,ControlSettingsDialog
from nova_control_center.online_updates import version_key,newer,allowed_asset,UpdateDialog

def test_pulse_native_label_offscreen(qtbot):
    from PySide6.QtWidgets import QLabel
    indicator=PulseIndicator(PALETTES["ElectroBlueNEON"])
    qtbot.addWidget(indicator)
    assert isinstance(indicator,QLabel)
    assert indicator.pixmap() is not None
    indicator.show()
    for _ in range(160):
        indicator.tick()
        QApplication.processEvents()
        assert indicator.pixmap().size().width()==28
    indicator.timer.stop()
    indicator.close()

def test_sessions_settings_paint_during_repeated_open(qtbot):
    for _ in range(12):
        for typ in (ControlSessionsDialog,ControlSettingsDialog):
            d=typ(PALETTES["ElectroBlueNEON"])
            qtbot.addWidget(d)
            d.show()
            for _ in range(4):
                d.update()
                QApplication.processEvents()
            d.close()

def test_releases_require_explicit_trust():
    assert version_key("2.4.1-dev0")== (2,4,1)
    assert newer("2.5.0")
    assert not newer("2.4.0")
    assert allowed_asset("https://github.com/org/repo/releases/download/v2.5/a.deb")
    assert not allowed_asset("http://github.com/org/repo/x")
    assert not allowed_asset("https://evil.example/download")
