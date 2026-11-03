"""Native Linux entry point for the NOVA CONTROL CENTER foundation."""
import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSplitter, QMessageBox
)

from .core import AppRegistry, AppSpec, EventBus
from .workspace import AppCatalog, Workspace
from .apps import TerminalDemo, FilesDemo, DockerDemo, WebPanel

CONFIG = Path.home() / ".config" / "nova-control-center" / "workspace.json"
THEME = Path(__file__).parent / "themes" / "nexus_hd.qss"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOVA CONTROL CENTER  —  NEXUS HD 0.8")
        self.resize(1440, 900)
        self.context = EventBus(self)
        self.registry = AppRegistry()
        for app_id, label, icon, factory in (
            ("terminal", "Terminal", "⌘", TerminalDemo),
            ("sftp", "SFTP Explorer", "▤", FilesDemo),
            ("web", "HTTPS Viewer", "◎", WebPanel),
            ("docker", "Docker Manager", "▣", DockerDemo),
        ):
            self.registry.register(AppSpec(app_id, label, icon, factory))

        center = QWidget()
        outer = QVBoxLayout(center)
        outer.setContentsMargins(12, 12, 12, 8)
        header = QHBoxLayout()
        name = QLabel("◈  NOVA CONTROL CENTER")
        name.setObjectName("brand")
        header.addWidget(name)
        header.addStretch()
        for label, handler in (
            ("CASCADE", lambda: self.workspace.cascadeSubWindows()),
            ("GRID", lambda: self.workspace.tileSubWindows()),
            ("SAVE", self.save_layout),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            header.addWidget(btn)
        outer.addLayout(header)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.catalog = AppCatalog(self.registry)
        self.catalog.itemDoubleClicked.connect(
            lambda item: self.workspace.open_app(item.data(Qt.ItemDataRole.UserRole))
        )
        self.workspace = Workspace(self.registry, self.context)
        split.addWidget(self.catalog)
        split.addWidget(self.workspace)
        split.setStretchFactor(1, 1)
        split.setSizes([190, 1100])
        outer.addWidget(split, 1)
        footer = QLabel("● NEXUS CORE ONLINE    |    FOUNDATION 0.1.0    |    DEMO MODULES • NO REMOTE COMMANDS")
        footer.setObjectName("footer")
        outer.addWidget(footer)
        self.setCentralWidget(center)
        self.restore_layout()

    def save_layout(self):
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps(self.workspace.snapshot(), indent=2), encoding="utf-8")

    def restore_layout(self):
        try:
            data = json.loads(CONFIG.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.workspace.restore_snapshot(data[:30])
                return
        except (OSError, ValueError, TypeError):
            pass
        self.workspace.open_app("terminal")
        self.workspace.open_app("sftp")
        self.workspace.open_app("web")
        self.workspace.tileSubWindows()

    def closeEvent(self, event):
        try:
            self.save_layout()
        except OSError:
            pass
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NOVA Control Center")
    if THEME.exists():
        app.setStyleSheet(THEME.read_text(encoding="utf-8"))
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
