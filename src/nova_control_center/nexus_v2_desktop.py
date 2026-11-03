"""NEXUS NOVA HD V2: frameless native MDI with painted frames and app catalog."""
from PySide6.QtCore import Qt, Signal, QMimeData, QPoint, QRectF, QTimer
from PySide6.QtGui import QDrag, QPainter, QPen, QBrush, QColor, QPixmap, QLinearGradient, QRadialGradient, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QMdiArea, QMdiSubWindow, QListWidget, QListWidgetItem,
    QLabel, QFrame, QPushButton, QHBoxLayout, QVBoxLayout, QLayout
)
from .nexus_v2_paint import draw_frame, qcolor, vector_icon, NexusBackdrop

MIME = "application/x-nova-control-app-id"

class AppShelf(QListWidget):
    launch_requested = Signal(str)
    def __init__(self, apps, palette, parent=None):
        super().__init__(parent)
        self.palette = palette
        self.setDragEnabled(True)
        self.setSpacing(5)
        self.setIconSize(__import__("PySide6.QtCore", fromlist=["QSize"]).QSize(23,23))
        for app in apps:
            item = QListWidgetItem(vector_icon(app.icon, palette.bright, 30), app.title)
            item.setData(Qt.ItemDataRole.UserRole, app.app_id)
            item.setToolTip("Double-clic pour ouvrir • Glisser vers l'espace de travail")
            self.addItem(item)
        self.itemDoubleClicked.connect(
            lambda item: self.launch_requested.emit(item.data(Qt.ItemDataRole.UserRole)))
    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item: return
        data = QMimeData()
        data.setData(MIME, str(item.data(Qt.ItemDataRole.UserRole)).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(data)
        drag.exec(Qt.DropAction.CopyAction)
    def set_palette(self, palette):
        self.palette = palette
        for row in range(self.count()):
            item = self.item(row)
            name = str(item.data(Qt.ItemDataRole.UserRole))
            specs = {
                "demo.terminal":"terminal", "demo.explorer":"folder",
                "demo.controls":"settings", "demo.events":"network",
            }
            item.setIcon(vector_icon(specs.get(name, "apps"), palette.bright, 30))

class WindowBar(QFrame):
    def __init__(self, host, descriptor, palette):
        super().__init__(host)
        self.host = host
        self.palette = palette
        self._offset = None
        self.setFixedHeight(38)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 4, 8, 3)
        row.setSpacing(3)
        self.logo = QLabel()
        self.logo.setPixmap(vector_icon(descriptor.icon, palette.bright, 26).pixmap(24,24))
        row.addWidget(self.logo)
        self.label = QLabel(descriptor.title)
        self.label.setObjectName("windowHeading")
        row.addWidget(self.label, 1)
        for key, tip, slot in (
            ("minimize", "Réduire", host.showMinimized),
            ("maximize", "Agrandir / restaurer", host.toggle_maximized),
            ("close", "Fermer", host.close),
        ):
            btn = QPushButton()
            btn.setObjectName("windowCtrl")
            btn.setFixedSize(25, 25)
            btn.setIcon(vector_icon(key, "#BDEAFF", 20))
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            row.addWidget(btn)
    def set_palette(self, palette, icon):
        self.palette = palette
        self.logo.setPixmap(vector_icon(icon, palette.bright, 26).pixmap(24,24))
        self.update()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._offset = event.globalPosition().toPoint() - self.host.mapToGlobal(QPoint())
            self.host.mdiArea().setActiveSubWindow(self.host)
            event.accept()
            return
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        if self._offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if not self.host.isMaximized():
                global_pos = event.globalPosition().toPoint() - self._offset
                self.host.move(self.host.parentWidget().mapFromGlobal(global_pos))
            event.accept()
            return
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        self._offset = None
        super().mouseReleaseEvent(event)
    def mouseDoubleClickEvent(self, event):
        self.host.toggle_maximized()
        event.accept()
    def paintEvent(self, event):
        p = QPainter(self)
        p.setPen(QPen(qcolor(self.palette.accent, 115), 1))
        p.drawLine(7, self.height()-2, self.width()-7, self.height()-2)
        p.end()
        super().paintEvent(event)

class CornerResize(QLabel):
    def __init__(self, host):
        super().__init__("◢")
        self.host = host
        self.start = None
        self.original = None
        self.setFixedSize(23,19)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("Redimensionner")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            self.start=event.globalPosition().toPoint()
            self.original=self.host.size()
            event.accept()
    def mouseMoveEvent(self,event):
        if self.start is not None and self.original is not None:
            delta=event.globalPosition().toPoint()-self.start
            self.host.resize(max(self.host.minimumWidth(),self.original.width()+delta.x()),
                             max(self.host.minimumHeight(),self.original.height()+delta.y()))
            event.accept()
    def mouseReleaseEvent(self,event):
        self.start=None
        self.original=None
        event.accept()

class NexusSubWindow(QMdiSubWindow):
    def __init__(self, descriptor, content, palette):
        super().__init__()
        self.app_id=descriptor.app_id
        self.descriptor=descriptor
        self.palette=palette
        self.phase=0.0
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setMinimumSize(descriptor.minimum[0],descriptor.minimum[1])
        box=QWidget()
        box.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout=QVBoxLayout(box)
        layout.setContentsMargins(10,10,10,9)
        layout.setSpacing(1)
        self.bar=WindowBar(self,descriptor,palette)
        layout.addWidget(self.bar)
        layout.addWidget(content,1)
        bottom=QHBoxLayout()
        bottom.setContentsMargins(0,0,0,0)
        bottom.addStretch()
        self.grip=CornerResize(self)
        bottom.addWidget(self.grip)
        layout.addLayout(bottom)
        self.setWidget(box)
        self.resize(510,340)
    def set_palette(self,palette):
        self.palette=palette
        self.bar.set_palette(palette,self.descriptor.icon)
        self.update()
    def toggle_maximized(self):
        if self.isMaximized(): self.showNormal()
        else: self.showMaximized()
    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_frame(p,QRectF(self.rect()).adjusted(5,5,-5,-5),self.palette,
                   1.22 if self.isActiveWindow() else 0.86,self.phase)
        p.end()
        super().paintEvent(event)

class NexusDesktop(QMdiArea):
    number_changed=Signal(int)
    def __init__(self, apps, bus, palette, parent=None):
        super().__init__(parent)
        self.registry={a.app_id:a for a in apps}
        self.bus=bus
        self.palette=palette
        self.counts={}
        self.setViewMode(QMdiArea.ViewMode.SubWindowView)
        self.setActivationOrder(QMdiArea.WindowOrder.StackingOrder)
        self.setAcceptDrops(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("QMdiArea{border:0;background:#07101C;}")
        self._base_color=palette.background
        self._update_wallpaper()
        self.subWindowActivated.connect(lambda _:self.number_changed.emit(len(self.subWindowList())))
        self.timer=QTimer(self)
        self.timer.setInterval(50)  # 20fps single active border only
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self.effect_enabled=True
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._update_wallpaper()

    def _update_wallpaper(self):
        """Render abstract PCB texture once per resize/theme change, not every frame."""
        width=max(1,self.viewport().width())
        height=max(1,self.viewport().height())
        pix=QPixmap(width,height)
        pix.fill(QColor(self.palette.background))
        p=QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad=QRadialGradient(width*.63,height*.28,max(1,width*.75))
        color=QColor(self.palette.accent)
        color.setAlpha(44)
        grad.setColorAt(0,color)
        grad.setColorAt(.7,QColor(7,17,31,40))
        grad.setColorAt(1,QColor(7,17,31,0))
        p.fillRect(0,0,width,height,grad)
        for i in range(33):
            side=i%2
            xx=22+(i*43)%max(1,int(width*.38))
            yy=14+(i*61)%max(1,height)
            x=xx if side==0 else width-xx
            sign=1 if side==0 else -1
            c=QColor(self.palette.accent)
            c.setAlpha(18+((i*17)%58))
            p.setPen(QPen(c,1.2))
            route=QPainterPath()
            route.moveTo(x,yy)
            route.lineTo(x+sign*(18+i%4*6),yy)
            route.lineTo(x+sign*(36+i%4*6),yy+18)
            route.lineTo(x+sign*(116+i%5*13),yy+18)
            p.drawPath(route)
            p.drawEllipse(x+sign*(116+i%5*13)-2,yy+16,4,4)
        p.end()
        self.setBackground(QBrush(pix))

    def _tick(self):
        if not self.effect_enabled or not self.isVisible(): return
        active=self.activeSubWindow()
        if isinstance(active,NexusSubWindow):
            active.phase=(active.phase+.013)%1.0
            active.update()
    def set_palette(self,palette):
        self.palette=palette
        self._update_wallpaper()
        for win in self.subWindowList():
            if isinstance(win,NexusSubWindow): win.set_palette(palette)
    def open_app(self,app_id,pos=None):
        if app_id not in self.registry: return None
        desc=self.registry[app_id]
        content=desc.factory(self.bus)
        win=NexusSubWindow(desc,content,self.palette)
        self.addSubWindow(win)
        self.counts[app_id]=self.counts.get(app_id,0)+1
        if pos is None:
            offset=(self.counts[app_id]-1)*26
            win.move(16+offset,16+offset)
        else: win.move(pos)
        win.show()
        self.setActiveSubWindow(win)
        self.number_changed.emit(len(self.subWindowList()))
        return win
    def dragEnterEvent(self,event):
        if event.mimeData().hasFormat(MIME):event.acceptProposedAction()
        else:super().dragEnterEvent(event)
    def dragMoveEvent(self,event):
        if event.mimeData().hasFormat(MIME):event.acceptProposedAction()
        else:super().dragMoveEvent(event)
    def dropEvent(self,event):
        if event.mimeData().hasFormat(MIME):
            name=bytes(event.mimeData().data(MIME)).decode("utf-8",errors="replace")
            if name in self.registry:
                self.open_app(name,event.position().toPoint())
                event.acceptProposedAction()
                return
        super().dropEvent(event)
    def snapshot(self):
        output=[]
        for win in self.subWindowList():
            if not isinstance(win,NexusSubWindow):continue
            rect=win.normalGeometry() if win.isMaximized() else win.geometry()
            output.append(dict(id=win.app_id,x=rect.x(),y=rect.y(),w=rect.width(),
                               h=rect.height(),maximized=win.isMaximized()))
        return output
    def restore_snapshot(self,items):
        if not isinstance(items,list):return False
        restored=0
        for item in items[:24]:
            if not isinstance(item,dict) or item.get("id") not in self.registry:continue
            try:
                win=self.open_app(item["id"])
                x=max(0,min(2800,int(item.get("x",15))))
                y=max(0,min(2000,int(item.get("y",15))))
                w=max(340,min(2200,int(item.get("w",510))))
                h=max(230,min(1600,int(item.get("h",340))))
                win.setGeometry(x,y,w,h)
                if item.get("maximized"):win.showMaximized()
                restored+=1
            except (TypeError,ValueError,OverflowError):
                continue
        return restored>0
