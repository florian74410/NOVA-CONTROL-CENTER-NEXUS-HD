"""V2 floating application windows, drag/drop, snap assist and workspace persistence."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPoint, QMimeData, Signal
from PySide6.QtGui import QDrag, QPainter, QPen, QColor, QPixmap
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QSizePolicy,
    QFrame, QListWidget, QListWidgetItem, QMdiArea, QMdiSubWindow,QMenu, QApplication)
from .v2_skin import NeonSurface, NeonButton, color, draw_bevel_panel, draw_glyph, trace

MIME="application/x-nova-control-app-id"

class AppCatalog(QListWidget):
    launch=Signal(str)
    def __init__(self,app_specs,parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSpacing(5)
        self.setMinimumWidth(160)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName("appCatalog")
        for s in app_specs:
            item=QListWidgetItem("   "+s.title)
            item.setData(Qt.ItemDataRole.UserRole,s.app_id)
            item.setToolTip("Glisser vers le bureau · double clic pour ouvrir")
            item.setSizeHint(item.sizeHint().expandedTo(__import__("PySide6.QtCore",fromlist=["QSize"]).QSize(145,43)))
            self.addItem(item)
        self.itemDoubleClicked.connect(lambda item:self.launch.emit(item.data(Qt.ItemDataRole.UserRole)))
    def startDrag(self,actions):
        item=self.currentItem()
        if not item:return
        mime=QMimeData()
        mime.setData(MIME,item.data(Qt.ItemDataRole.UserRole).encode())
        drag=QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)

class ResizeCorner(QLabel):
    def __init__(self,win):
        super().__init__("◢")
        self.win=win
        self.anchor=None
        self.start_size=None
        self.setFixedSize(19,18)
        self.setToolTip("Redimensionner")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("color:#65DFFF;background:transparent;")
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:
            self.anchor=e.globalPosition().toPoint()
            self.start_size=self.win.size()
            e.accept()
    def mouseMoveEvent(self,e):
        if self.anchor is not None:
            d=e.globalPosition().toPoint()-self.anchor
            self.win.resize(max(self.win.minimumWidth(),self.start_size.width()+d.x()),
                            max(self.win.minimumHeight(),self.start_size.height()+d.y()))
            e.accept()
    def mouseReleaseEvent(self,e):
        self.anchor=None
        self.start_size=None
        e.accept()

class AppChrome(QFrame):
    def __init__(self,host,title,glyph,theme):
        super().__init__(host)
        self.host=host
        self.theme=theme
        self.setFixedHeight(42)
        self.setAutoFillBackground(False)
        self._drag_delta=None
        lay=QHBoxLayout(self)
        lay.setContentsMargins(12,4,8,4)
        lay.setSpacing(5)
        from .v2_skin import icon
        emblem=QLabel()
        emblem.setFixedSize(26,26)
        emblem.setPixmap(icon(glyph,theme,23).pixmap(23,23))
        self.emblem=emblem
        self.glyph=glyph
        lay.addWidget(emblem)
        self.title=QLabel(title.upper())
        self.title.setStyleSheet("font-size:11px;font-weight:bold;color:#DEF5FF;")
        lay.addWidget(self.title,1)
        self.controls=[]
        for kind,callback in (("minimize",host.showMinimized),
                             ("maximize",host.toggle_maximized),
                             ("close",host.close)):
            btn=NeonButton("",kind,theme,compact=True)
            btn.setFixedSize(29,27)
            btn.setToolTip({"minimize":"Réduire","maximize":"Maximiser / restaurer","close":"Fermer"}[kind])
            btn.clicked.connect(callback)
            lay.addWidget(btn)
            self.controls.append(btn)
    def apply_theme(self,theme):
        from .v2_skin import icon
        self.theme=theme
        self.emblem.setPixmap(icon(self.glyph,theme,23).pixmap(23,23))
        for b in self.controls:b.apply_theme(theme)
        self.update()
    def paintEvent(self,e):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r=QRectF(self.rect())
        p.fillRect(r,color(self.theme.panel,225))
        p.setPen(QPen(color(self.theme.accent,185),1))
        p.drawLine(3,self.height()-1,self.width()-3,self.height()-1)
        p.setPen(QPen(color(self.theme.light,48),3))
        p.drawLine(24,2,min(160,self.width()-20),2)
        trace(p,[(self.width()*.55,4),(self.width()*.60,4),
                 (self.width()*.63,15),(self.width()*.71,15)],self.theme.accent,105)
        p.end()
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:
            self._drag_delta=e.globalPosition().toPoint()-self.host.mapToGlobal(QPoint(0,0))
            self.host.setFocus()
            e.accept()
    def mouseMoveEvent(self,e):
        if self._drag_delta is not None and e.buttons() & Qt.MouseButton.LeftButton:
            if not self.host.isMaximized():
                parent=self.host.parentWidget()
                pos=parent.mapFromGlobal(e.globalPosition().toPoint()-self._drag_delta)
                self.host.move(max(0,pos.x()),max(0,pos.y()))
            e.accept()
    def mouseReleaseEvent(self,e):
        self._drag_delta=None
        e.accept()
    def mouseDoubleClickEvent(self,e):
        self.host.toggle_maximized()
        e.accept()

class AppWindow(QMdiSubWindow):
    def __init__(self,spec,content,theme):
        super().__init__()
        self.app_id=spec.app_id
        self.theme=theme
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumSize(325,230)
        self.shell=NeonSurface(theme,cut=13,routing=True)
        self.shell.setObjectName("appShell")
        layout=QVBoxLayout(self.shell)
        layout.setContentsMargins(5,5,5,4)
        layout.setSpacing(0)
        self.chrome=AppChrome(self,spec.title,spec.glyph,theme)
        layout.addWidget(self.chrome)
        content.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        layout.addWidget(content,1)
        foot=QHBoxLayout()
        foot.setContentsMargins(5,0,1,0)
        status=QLabel("● NOVA APP  ·  LOCAL / DEMO")
        status.setStyleSheet("font-size:9px;color:#648CA8;")
        foot.addWidget(status)
        foot.addStretch(1)
        foot.addWidget(ResizeCorner(self))
        layout.addLayout(foot)
        self.setWidget(self.shell)
        self.resize(540,360)
    def apply_theme(self,theme):
        self.theme=theme
        self.shell.apply_theme(theme)
        self.chrome.apply_theme(theme)
    def toggle_maximized(self):
        if self.isMaximized():self.showNormal()
        else:self.showMaximized()

class Workspace(QMdiArea):
    number_changed=Signal(int)
    def __init__(self,specs,context,theme,parent=None):
        super().__init__(parent)
        self.specs={s.app_id:s for s in specs}
        self.context=context
        self.theme=theme
        self.counts={}
        self._art_cache={}
        self.setAcceptDrops(True)
        self.setViewMode(QMdiArea.ViewMode.SubWindowView)
        self.setActivationOrder(QMdiArea.WindowOrder.StackingOrder)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setAutoFillBackground(False)
        self.subWindowActivated.connect(lambda _:self.number_changed.emit(len(self.subWindowList())))
    def set_theme(self,theme):
        self.theme=theme
        for w in self.subWindowList():
            if isinstance(w,AppWindow):w.apply_theme(theme)
        self.viewport().update()
    def drawBackground(self,painter,rect):
        painter.save()
        r=QRectF(self.viewport().rect())
        painter.fillRect(r,color(self.theme.bg))
        # Native PCB routing is regenerated at current viewport size: no stretched bitmaps.
        w,h=r.width(),r.height()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Optional user art-pack texture. Native Qt PCB remains functional without it.
        art_root=Path(__file__).resolve().parents[2] / "Assets" / "Generated"
        art_path=art_root / self.theme.name / "Backgrounds" / "pcb_tile.png"
        cache_key=str(art_path)
        if cache_key not in self._art_cache:
            self._art_cache[cache_key]=QPixmap(cache_key) if art_path.is_file() else QPixmap()
        pattern=self._art_cache[cache_key]
        if not pattern.isNull():
            painter.save()
            painter.setOpacity(0.16)
            painter.drawTiledPixmap(self.viewport().rect(),pattern)
            painter.restore()
        for i in range(9):
            delta=i*22
            trace(painter,[(6+delta,0),(6+delta,30+delta),
                           (20+delta,44+delta),(140+delta,44+delta)],
                  self.theme.accent,26+i%3*10,1.05)
            trace(painter,[(w-8-delta,h),(w-8-delta,h-34-delta),
                           (w-22-delta,h-48-delta),(w-143-delta,h-48-delta)],
                  self.theme.accent,24+i%3*10,1.05)
        painter.setPen(QPen(color(self.theme.accent,12),1))
        for x in range(0,int(w),40):painter.drawLine(x,0,x,int(h))
        for y in range(0,int(h),40):painter.drawLine(0,y,int(w),y)
        painter.restore()
    def open_app(self,app_id,pos=None):
        spec=self.specs.get(app_id)
        if spec is None:return None
        content=spec.factory(self.context)
        win=AppWindow(spec,content,self.theme)
        self.addSubWindow(win)
        count=self.counts.get(app_id,0)+1
        self.counts[app_id]=count
        if pos is None:pos=QPoint(18+(count-1)*33,22+(count-1)*33)
        win.move(pos)
        win.show()
        self.setActiveSubWindow(win)
        self.number_changed.emit(len(self.subWindowList()))
        return win
    def dragEnterEvent(self,e):
        if e.mimeData().hasFormat(MIME):e.acceptProposedAction()
        else:super().dragEnterEvent(e)
    def dragMoveEvent(self,e):
        if e.mimeData().hasFormat(MIME):e.acceptProposedAction()
        else:super().dragMoveEvent(e)
    def dropEvent(self,e):
        if e.mimeData().hasFormat(MIME):
            app=bytes(e.mimeData().data(MIME)).decode(errors="replace")
            if app in self.specs:
                self.open_app(app,e.position().toPoint())
                e.acceptProposedAction()
                return
        super().dropEvent(e)
    def contextMenuEvent(self,e):
        menu=QMenu(self)
        group=menu.addMenu("⊞  Ouvrir une application")
        for spec in self.specs.values():
            action=group.addAction(spec.title)
            action.triggered.connect(lambda checked=False,id=spec.app_id:self.open_app(id))
        menu.addSeparator()
        menu.addAction("▦  Mosaïque",self.tileSubWindows)
        menu.addAction("▣  Cascade",self.cascadeSubWindows)
        menu.exec(e.globalPos())
    def snapshot(self):
        result=[]
        for win in self.subWindowList():
            if not isinstance(win,AppWindow):continue
            g=win.normalGeometry() if win.isMaximized() else win.geometry()
            result.append(dict(app_id=win.app_id,x=g.x(),y=g.y(),
                               width=g.width(),height=g.height(),maximized=win.isMaximized()))
        return result
    def restore_snapshot(self,values):
        if not isinstance(values,list):return False
        restored=0
        for item in values[:24]:
            if not isinstance(item,dict) or item.get("app_id") not in self.specs:continue
            try:
                win=self.open_app(item["app_id"])
                win.setGeometry(max(0,min(2500,int(item.get("x",20)))),
                    max(0,min(2500,int(item.get("y",20)))),
                    max(325,min(2300,int(item.get("width",540)))),
                    max(230,min(1600,int(item.get("height",360)))))
                if item.get("maximized"):win.showMaximized()
                restored+=1
            except (TypeError,ValueError):
                continue
        return restored>0
