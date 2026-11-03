"""Freeform MDI workspace with application drag/drop and saved geometry."""
import json
from pathlib import Path
from PySide6.QtCore import Qt, QMimeData, QPoint, QByteArray
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMdiArea, QMdiSubWindow

MIME = "application/x-nova-app-id"

class AppCatalog(QListWidget):
    def __init__(self, registry, parent=None):
        super().__init__(parent)
        self.setObjectName("appCatalog")
        self.setDragEnabled(True)
        self.setSpacing(6)
        self.setMinimumWidth(170)
        for spec in registry.all():
            item = QListWidgetItem(spec.icon + "   " + spec.label)
            item.setData(Qt.ItemDataRole.UserRole, spec.app_id)
            self.addItem(item)

    def startDrag(self, actions):
        item = self.currentItem()
        if not item:
            return
        mime = QMimeData()
        mime.setData(MIME, item.data(Qt.ItemDataRole.UserRole).encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)

class Workspace(QMdiArea):
    def __init__(self, registry, context, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.context = context
        self.setObjectName("workspace")
        self.setAcceptDrops(True)
        self.setViewMode(QMdiArea.ViewMode.SubWindowView)
        self.setActivationOrder(QMdiArea.WindowOrder.StackingOrder)
        self._counts = {}

    def open_app(self, app_id, position=None):
        spec = self.registry.get(app_id)
        self._counts[app_id] = self._counts.get(app_id, 0) + 1
        window = QMdiSubWindow()
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        window.setWindowTitle(f"{spec.label}  #{self._counts[app_id]}")
        window.setWidget(spec.factory(self.context))
        self.addSubWindow(window)
        window.resize(470, 310)
        if position is not None:
            window.move(position)
        window.show()
        self.setActiveSubWindow(window)
        return window

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
            app_id = bytes(event.mimeData().data(MIME)).decode()
            if app_id in {s.app_id for s in self.registry.all()}:
                self.open_app(app_id, event.position().toPoint())
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def snapshot(self):
        result = []
        for win in self.subWindowList():
            title = win.windowTitle()
            app_id = None
            for spec in self.registry.all():
                if title.startswith(spec.label + "  #"):
                    app_id = spec.app_id
                    break
            if app_id:
                g = win.geometry()
                result.append({"app_id": app_id, "x": g.x(), "y": g.y(),
                               "width": g.width(), "height": g.height()})
        return result

    def restore_snapshot(self, entries):
        for item in entries:
            app_id = item.get("app_id")
            if app_id not in {s.app_id for s in self.registry.all()}:
                continue
            win = self.open_app(app_id, QPoint(max(0, int(item.get("x", 0))),
                                               max(0, int(item.get("y", 0)))))
            win.resize(max(220, int(item.get("width", 470))),
                       max(160, int(item.get("height", 310))))
