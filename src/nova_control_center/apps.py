"""Initial native application panels. No live remote connection in foundation 0.1."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QPlainTextEdit,
    QTreeWidget, QTreeWidgetItem, QHBoxLayout, QLineEdit
)

def panel(title, description):
    w = QWidget()
    v = QVBoxLayout(w)
    heading = QLabel(title)
    heading.setObjectName("panelHeading")
    v.addWidget(heading)
    v.addWidget(QLabel(description))
    return w, v

class TerminalDemo(QWidget):
    def __init__(self, context):
        super().__init__()
        v = QVBoxLayout(self)
        t = QLabel("TERMINAL  /  LOCAL DEMONSTRATION")
        t.setObjectName("panelHeading")
        v.addWidget(t)
        output = QPlainTextEdit()
        output.setObjectName("terminal")
        output.setReadOnly(True)
        output.setPlainText("NOVA TERMINAL — visual prototype\nSSH not connected in v0.1\n\n$ _")
        v.addWidget(output, 1)
        self.output = output
        btn = QPushButton("Generate demonstration event")
        btn.clicked.connect(lambda: context.publish("file.changed", {"path": "/demo/config.json"}))
        v.addWidget(btn)

class FilesDemo(QWidget):
    def __init__(self, context):
        super().__init__()
        w, v = panel("SFTP EXPLORER", "Demonstration tree — no remote filesystem access")
        layout = QVBoxLayout(self)
        while v.count():
            item = v.takeAt(0)
            if item.widget():
                item.widget().setParent(self)
                layout.addWidget(item.widget())
        tree = QTreeWidget()
        tree.setHeaderLabels(["Name", "Status"])
        root = QTreeWidgetItem(["/demo", "local"])
        for name in ("App", "Docker", "Logs", "config.json"):
            root.addChild(QTreeWidgetItem([name, "mock"]))
        tree.addTopLevelItem(root)
        tree.expandAll()
        layout.addWidget(tree, 1)
        status = QLabel("Sync: idle")
        layout.addWidget(status)
        def on_event(name, payload):
            if name == "file.changed" and isinstance(payload, dict):
                status.setText("Sync event: " + str(payload.get("path", "?")))
        context.event.connect(on_event)

class DockerDemo(QWidget):
    def __init__(self, context):
        super().__init__()
        w, v = panel("DOCKER", "Connection adapter planned for a later version")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("DOCKER MANAGER  /  OFFLINE MOCKUP"))
        layout.addWidget(QLabel("No container commands are executed in this build."))
        layout.addStretch(1)

class WebPanel(QWidget):
    def __init__(self, context):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("WEB VIEW  /  HTTPS")
        label.setObjectName("panelHeading")
        layout.addWidget(label)
        row = QHBoxLayout()
        address = QLineEdit("https://example.org")
        go = QPushButton("Open")
        row.addWidget(address, 1)
        row.addWidget(go)
        layout.addLayout(row)
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            fallback = QLabel("Qt WebEngine unavailable. Install optional WebEngine component.")
            fallback.setWordWrap(True)
            layout.addWidget(fallback)
            go.setEnabled(False)
        else:
            from PySide6.QtCore import QUrl
            browser = QWebEngineView(self)
            layout.addWidget(browser, 1)
            def navigate():
                url = QUrl.fromUserInput(address.text())
                if url.scheme() == "https":
                    browser.setUrl(url)
            go.clicked.connect(navigate)
            navigate()
