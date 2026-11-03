"""Frameless resizable MDI subwindows and drag/drop workspace."""
from PySide6.QtCore import Qt, QPoint, QMimeData, Signal
from PySide6.QtGui import QDrag, QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QMdiArea, QMdiSubWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizeGrip, QFrame, QListWidget, QListWidgetItem
)
from .nexus_theme import CircuitCanvas, rgba

MIME = "application/x-nova-control-app-id"

class AppRail(QListWidget):
    launch_requested = Signal(str)
    def __init__(self, apps, parent=None):
        super().__init__(parent)
        self.setObjectName("appRail")
        self.setSpacing(6)
        self.setDragEnabled(True)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setMinimumWidth(150)
        for app in apps:
            item = QListWidgetItem(f"{app.glyph}  {app.title}")
            item.setData(Qt.ItemDataRole.UserRole, app.app_id)
            item.setToolTip("Glisser vers le bureau ou double-cliquer")
            self.addItem(item)
        self.itemDoubleClicked.connect(
            lambda item: self.launch_requested.emit(item.data(Qt.ItemDataRole.UserRole))
        )

    def startDrag(self, actions):
        item = self.currentItem()
        if item is None:
            return
        data = QMimeData()
        data.setData(MIME, str(item.data(Qt.ItemDataRole.UserRole)).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(data)
        drag.exec(Qt.DropAction.CopyAction)

class TitleBar(QFrame):
    def __init__(self, host, title, icon):
        super().__init__(host)
        self.host = host
        self._drag_offset = None
        self.setFixedHeight(34)
        self.setStyleSheet("QFrame { background: #10304A; border-bottom: 1px solid #248CC2; }")
        row = QHBoxLayout(self)
        row.setContentsMargins(9, 2, 5, 2)
        row.setSpacing(3)
        self.title = QLabel(f"{icon}   {title}")
        self.title.setStyleSheet("color: #8FDEFF; font-size: 11px; font-weight: bold; border: 0;")
        row.addWidget(self.title, 1)
        for label, tooltip, callback in (
            ("—", "Réduire", host.showMinimized),
            ("□", "Agrandir / restaurer", host.toggle_maximized),
            ("×", "Fermer", host.close),
        ):
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.setFixedSize(27, 25)
            btn.setStyleSheet("QPushButton{background:transparent;border:0;color:#C7EEFF;padding:0;} QPushButton:hover{background:#235475;}")
            btn.clicked.connect(callback)
            row.addWidget(btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.host.mapToGlobal(QPoint(0, 0))
            self.host.setFocus()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            if not self.host.isMaximized():
                target = event.globalPosition().toPoint() - self._drag_offset
                parent = self.host.parentWidget()
                if parent is not None:
                    self.host.move(parent.mapFromGlobal(target))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.host.toggle_maximized()

class NovaSubWindow(QMdiSubWindow):
    def __init__(self, descriptor, content):
        super().__init__()
        self.app_id = descriptor.app_id
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumSize(descriptor.min_width, descriptor.min_height)
        container = QFrame()
        container.setObjectName("novaAppShell")
        container.setStyleSheet("QFrame#novaAppShell {background:#091C30;border:1px solid #28A8DE;border-radius:5px;}")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        layout.addWidget(TitleBar(self, descriptor.title, descriptor.glyph))
        layout.addWidget(content, 1)
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 1, 1)
        grip_row.addStretch()
        grip = QSizeGrip(container)
        grip.setFixedSize(16, 16)
        grip_row.addWidget(grip)
        layout.addLayout(grip_row)
        self.setWidget(container)
        self.resize(490, 330)

    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

class NovaDesktop(QMdiArea):
    number_changed = Signal(int)
    def __init__(self, apps, context, theme, parent=None):
        super().__init__(parent)
        self.app_map = {a.app_id: a for a in apps}
        self.context = context
        self.theme = theme
        self.counters = {}
        self.setAcceptDrops(True)
        self.setViewMode(QMdiArea.ViewMode.SubWindowView)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setActivationOrder(QMdiArea.WindowOrder.StackingOrder)
        self.setStyleSheet("QMdiArea { background: #07101E; border: 1px solid #276B8C; }")
        self.subWindowActivated.connect(lambda _: self.number_changed.emit(len(self.subWindowList())))

    def open_app(self, app_id, pos=None):
        if app_id not in self.app_map:
            return None
        app = self.app_map[app_id]
        content = app.factory(self.context)
        win = NovaSubWindow(app, content)
        self.addSubWindow(win)
        self.counters[app_id] = self.counters.get(app_id, 0) + 1
        if pos is not None:
            win.move(pos)
        else:
            offset = (self.counters[app_id] - 1) * 28
            win.move(22 + offset, 24 + offset)
        win.show()
        self.setActiveSubWindow(win)
        self.number_changed.emit(len(self.subWindowList()))
        return win

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(MIME):
            app_id = bytes(event.mimeData().data(MIME)).decode("utf-8", errors="replace")
            if app_id in self.app_map:
                self.open_app(app_id, event.position().toPoint())
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def snapshot(self):
        result = []
        for win in self.subWindowList():
            if isinstance(win, NovaSubWindow):
                g = win.normalGeometry() if win.isMaximized() else win.geometry()
                result.append(dict(app_id=win.app_id, x=g.x(), y=g.y(),
                                   width=g.width(), height=g.height(),
                                   maximized=win.isMaximized()))
        return result

    def restore_snapshot(self, data):
        if not isinstance(data, list):
            return False
        restored = 0
        for obj in data[:25]:
            if not isinstance(obj, dict) or obj.get("app_id") not in self.app_map:
                continue
            try:
                win = self.open_app(obj["app_id"])
                x = max(0, min(3000, int(obj.get("x", 20))))
                y = max(0, min(3000, int(obj.get("y", 20))))
                w = max(300, min(2400, int(obj.get("width", 490))))
                h = max(220, min(1600, int(obj.get("height", 330))))
                win.setGeometry(x, y, w, h)
                if obj.get("maximized") is True:
                    win.showMaximized()
                restored += 1
            except (ValueError, TypeError):
                continue
        return restored > 0
