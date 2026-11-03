"""NOVA CONTROL CENTER V1: native multi-window NEXUS HUD shell."""
import json
import sys
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Qt, QTimer
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QMenu, QSplitter, QMessageBox, QInputDialog
)
from .nexus_theme import PALETTES, stylesheet, NovaLogo
from .nexus_apps import BUILTIN_APPS, AppContext
from .nexus_desktop import AppRail, NovaDesktop

SETTINGS_FILE = Path.home() / ".config" / "nova-control-center" / "v1.json"

class Bus(QObject):
    event = Signal(str, object)
    def publish(self, name, payload=None):
        self.event.emit(name, payload)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOVA CONTROL CENTER — NEXUS HD V1")
        self.resize(1450, 880)
        self.bus = Bus(self)
        self.context = AppContext(self.bus)
        self.state = self._load_state()
        self.theme_name = self.state.get("theme", "ElectroBlueNEON")
        if self.theme_name not in PALETTES:
            self.theme_name = "ElectroBlueNEON"
        self._build_ui()
        self._apply_theme()
        if not self.desktop.restore_snapshot(self.state.get("workspace")):
            self.desktop.open_app("demo.terminal")
            self.desktop.open_app("demo.explorer")
            self.desktop.open_app("demo.controls")
            self.desktop.open_app("demo.events")
            self.desktop.tileSubWindows()
        self._refresh_status()

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(8, 7, 8, 4)
        outer.setSpacing(7)

        self.topbar = QWidget()
        self.topbar.setObjectName("topbar")
        self.topbar.setFixedHeight(55)
        h = QHBoxLayout(self.topbar)
        h.setContentsMargins(15, 4, 10, 4)
        logo = NovaLogo(PALETTES[self.theme_name])
        self.logo = logo
        h.addWidget(logo)
        self.brand = QLabel("NOVA CONTROL CENTER")
        self.brand.setObjectName("brand")
        h.addWidget(self.brand)
        self.subtitle = QLabel("  NEXUS HD / V1  ·  ELECTRONIC WORKSPACE")
        self.subtitle.setObjectName("muted")
        h.addWidget(self.subtitle)
        h.addStretch(1)
        for icon, label, action in (
            ("⊞", "Mosaïque", lambda: self.desktop.tileSubWindows()),
            ("▣", "Cascade", lambda: self.desktop.cascadeSubWindows()),
            ("↧", "Enregistrer l'espace", self.save_state),
        ):
            btn = QPushButton(icon + "  " + label)
            btn.setToolTip(label)
            btn.clicked.connect(action)
            h.addWidget(btn)
        self.theme_button = QPushButton("◈  THÈME")
        self.theme_button.setMenu(self._make_theme_menu())
        h.addWidget(self.theme_button)
        menu_btn = QPushButton("☰")
        menu_btn.setToolTip("Menu principal")
        menu_btn.setMenu(self._make_main_menu())
        h.addWidget(menu_btn)
        outer.addWidget(self.topbar)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(8, 12, 8, 8)
        side.setSpacing(8)
        label = QLabel("▤  APPLICATIONS")
        label.setObjectName("section")
        side.addWidget(label)
        self.catalog = AppRail(BUILTIN_APPS)
        self.catalog.launch_requested.connect(self._open)
        side.addWidget(self.catalog, 1)
        btn = QPushButton("⊕  Ajouter une application")
        btn.setToolTip("Intégration future par manifeste (non disponible dans la V1)")
        btn.clicked.connect(self._app_info)
        side.addWidget(btn)
        label2 = QLabel("◈  WORKSPACES")
        label2.setObjectName("section")
        side.addWidget(label2)
        save_btn = QPushButton("▣  Sauvegarder")
        save_btn.clicked.connect(self.save_state)
        side.addWidget(save_btn)
        split.addWidget(self.sidebar)
        self.desktop = NovaDesktop(BUILTIN_APPS, self.context, PALETTES[self.theme_name])
        self.desktop.number_changed.connect(self._refresh_status)
        split.addWidget(self.desktop)
        split.setStretchFactor(1, 1)
        split.setSizes([225, 1180])
        outer.addWidget(split, 1)

        self.footer = QWidget()
        self.footer.setFixedHeight(30)
        footer = QHBoxLayout(self.footer)
        footer.setContentsMargins(8, 1, 8, 1)
        footer.setSpacing(10)
        self.status_label = QLabel("●  NOVA CORE READY")
        self.count_label = QLabel("Fenêtres : 0")
        self.theme_label = QLabel("")
        for item in (self.status_label, self.count_label, self.theme_label):
            item.setObjectName("status")
            item.setFont(QFont("DejaVu Sans", 11))
        footer.addWidget(self.status_label)
        footer.addStretch()
        footer.addWidget(self.count_label)
        footer.addWidget(self.theme_label)
        self.footer.setStyleSheet("border-top: 1px solid #276B8C;")
        outer.addWidget(self.footer)
        self.bus.event.connect(self._on_event)

        quick = QAction("Palette de commandes", self)
        quick.setShortcut(QKeySequence("Ctrl+K"))
        quick.triggered.connect(self._command_palette)
        self.addAction(quick)

    def _make_theme_menu(self):
        menu = QMenu(self)
        for key in PALETTES:
            action = menu.addAction(("◉  " if key == self.theme_name else "◯  ") + key)
            action.triggered.connect(lambda checked=False, name=key: self.set_theme(name))
        return menu

    def _make_main_menu(self):
        menu = QMenu(self)
        for text, slot in (
            ("⊞  Organiser en mosaïque", lambda: self.desktop.tileSubWindows()),
            ("▣  Organiser en cascade", lambda: self.desktop.cascadeSubWindows()),
            ("⌕  Palette de commandes   Ctrl+K", self._command_palette),
            ("↧  Sauvegarder l'espace", self.save_state),
            ("ⓘ  À propos", self._about),
        ):
            a = menu.addAction(text)
            a.triggered.connect(slot)
        return menu

    def _command_palette(self):
        labels = [f"Ouverture : {a.title}" for a in BUILTIN_APPS] + [
            "Disposition : mosaïque", "Disposition : cascade",
            "Thème : ElectroBlueNEON", "Thème : RougeERROR",
            "Sauvegarder l'espace"
        ]
        label, ok = QInputDialog.getItem(self, "NEXUS / Command Palette", "Action :", labels, 0, False)
        if not ok:
            return
        if label.startswith("Ouverture : "):
            title = label.split(": ", 1)[1]
            for app in BUILTIN_APPS:
                if app.title == title:
                    self._open(app.app_id)
                    break
        elif label.endswith("mosaïque"):
            self.desktop.tileSubWindows()
        elif label.endswith("cascade"):
            self.desktop.cascadeSubWindows()
        elif label.startswith("Thème : "):
            self.set_theme(label.split(": ", 1)[1])
        elif label == "Sauvegarder l'espace":
            self.save_state()

    def contextMenuEvent(self, event):
        menu = self._make_main_menu()
        menu.exec(event.globalPos())

    def _open(self, app_id):
        self.desktop.open_app(app_id)
        self._refresh_status()

    def _refresh_status(self, *_args):
        if hasattr(self, "count_label"):
            self.count_label.setText(f"Fenêtres : {len(self.desktop.subWindowList())}")
            self.theme_label.setText("  |  " + self.theme_name)

    def _on_event(self, name, payload):
        self.status_label.setText("●  " + name[:45])

    def set_theme(self, key):
        if key not in PALETTES:
            return
        self.theme_name = key
        self._apply_theme()

    def _apply_theme(self):
        pal = PALETTES[self.theme_name]
        QApplication.instance().setStyleSheet(stylesheet(pal))
        self.desktop.set_palette(pal)
        self.logo.set_palette(pal)
        self.footer.setStyleSheet(f"border-top: 1px solid {pal.edge};")
        self.theme_button.setMenu(self._make_theme_menu())
        self._refresh_status()

    def _app_info(self):
        QMessageBox.information(self, "NOVA App Manager",
            "La V1 comprend quatre modules Qt de démonstration.\n"
            "Le chargement de modules Qt externes approuvés et leurs manifestes est prévu après validation du socle.")

    def _about(self):
        QMessageBox.information(self, "À propos",
            "NOVA CONTROL CENTER — NEXUS HD V1\n"
            "Bureau multi-fenêtres natif PySide6 / Qt 6.\n"
            "Modules de démonstration uniquement : aucun accès SSH, SFTP ou Docker.")

    def _load_state(self):
        try:
            value = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (ValueError, OSError):
            return {}

    def save_state(self):
        data = {"version": 1, "theme": self.theme_name, "workspace": self.desktop.snapshot()}
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = SETTINGS_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(SETTINGS_FILE)
            self.status_label.setText("●  Espace enregistré")
        except OSError as ex:
            QMessageBox.warning(self, "Enregistrement impossible", str(ex))

    def closeEvent(self, event):
        self.save_state()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NOVA CONTROL CENTER")
    app.setOrganizationName("NOVA")
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
