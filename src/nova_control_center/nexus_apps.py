"""Signed-off bundled demonstration applications; no remote commands in v1."""
from dataclasses import dataclass
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QPlainTextEdit, QVBoxLayout, QPushButton, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QCheckBox, QComboBox, QProgressBar
)
from PySide6.QtGui import QFont

@dataclass(frozen=True)
class AppDescriptor:
    app_id: str
    title: str
    glyph: str
    factory: object
    min_width: int = 300
    min_height: int = 220

class AppContext:
    def __init__(self, bus):
        self.bus = bus

    def publish(self, name, payload):
        self.bus.publish(name, payload)

class TerminalPreview(QWidget):
    def __init__(self, context):
        super().__init__()
        layout = QVBoxLayout(self)
        head = QLabel("▣  NEXUS TERMINAL  /  DEMO SESSION")
        head.setObjectName("section")
        layout.addWidget(head)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        font = QFont("DejaVu Sans Mono", 10)
        self.output.setFont(font)
        self.output.setPlainText("NOVA / local demo\nConnection status: OFFLINE (preview)\n\n$ nova --status\nNEXUS CORE READY\n\n$ _")
        layout.addWidget(self.output, 1)
        btn = QPushButton("⟳  Publier un événement de test")
        btn.clicked.connect(lambda: context.publish("demo.file.changed", {"path": "/demo/nova.json"}))
        layout.addWidget(btn)

class ExplorerPreview(QWidget):
    def __init__(self, context):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("▤  EXPLORATEUR  /  FICHIERS DE DÉMO")
        label.setObjectName("section")
        layout.addWidget(label)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nom", "État"])
        root = QTreeWidgetItem(["NOVA PROJECT", "local"])
        for name in ("Assets", "Applications", "Configs", "nova.json"):
            root.addChild(QTreeWidgetItem([name, "démo"]))
        self.tree.addTopLevelItem(root)
        self.tree.expandAll()
        layout.addWidget(self.tree, 1)
        self.status = QLabel("Synchronisation : en attente")
        layout.addWidget(self.status)
        context.bus.event.connect(self.on_event)

    def on_event(self, name, payload):
        if name == "demo.file.changed":
            self.status.setText("Événement reçu : " + str(payload.get("path", "")))

class ControlsPreview(QWidget):
    def __init__(self, context):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("◈  NOVA UI / WIDGET LAB")
        label.setObjectName("section")
        layout.addWidget(label)
        form = QHBoxLayout()
        field = QLineEdit()
        field.setPlaceholderText("Rechercher...")
        form.addWidget(field)
        form.addWidget(QPushButton("⌕"))
        layout.addLayout(form)
        row = QHBoxLayout()
        row.addWidget(QPushButton("✓  Appliquer"))
        row.addWidget(QPushButton("↻  Réinitialiser"))
        layout.addLayout(row)
        layout.addWidget(QCheckBox("Activer les effets lumineux"))
        combo = QComboBox()
        combo.addItems(["ElectroBlueNEON", "RougeERROR", "Native"])
        layout.addWidget(combo)
        bar = QProgressBar()
        bar.setValue(68)
        layout.addWidget(bar)
        layout.addStretch(1)

class EventPreview(QWidget):
    def __init__(self, context):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("⟡  NEXUS EVENT MONITOR")
        title.setObjectName("section")
        layout.addWidget(title)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlainText("Bus d'événements prêt.\n")
        layout.addWidget(self.log)
        context.bus.event.connect(self.on_event)

    def on_event(self, name, payload):
        self.log.appendPlainText(f"{name}  {payload}")

BUILTIN_APPS = (
    AppDescriptor("demo.terminal", "NOVA Terminal", "⌘", TerminalPreview),
    AppDescriptor("demo.explorer", "NOVA Explorer", "▤", ExplorerPreview),
    AppDescriptor("demo.controls", "Widgets & thèmes", "◈", ControlsPreview),
    AppDescriptor("demo.events", "NEXUS Events", "⟡", EventPreview),
)
