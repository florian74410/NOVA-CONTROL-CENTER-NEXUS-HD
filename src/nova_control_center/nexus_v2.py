"""NOVA CONTROL CENTER V2 — FULL QT NEXUS HD desktop.
No Electron, no web-based desktop shell. Remote apps are demos until adapters exist.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QSize, QRectF
from PySide6.QtGui import QFont, QKeySequence, QAction, QColor, QPainter
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QHBoxLayout,
    QVBoxLayout, QSplitter, QMenu, QMessageBox, QInputDialog
)
from .nexus_theme import PALETTES
from .nexus_v2_paint import vector_icon, draw_frame, qcolor, NexusPanel, NexusButton
from .nexus_v2_apps import BUILTIN_V2
from .nexus_v2_desktop import AppShelf, NexusDesktop

SETTINGS = Path.home()/".config"/"nova-control-center"/"v2.json"

class EventBus(QObject):
    event = Signal(str,object)
    def publish(self,name,data=None):
        self.event.emit(name,data)

def qss(p):
    return """
    QWidget {color:#D9EDFA;font-family:'DejaVu Sans','Noto Sans',sans-serif;font-size:12px;}
    QWidget#root {background:%s;}
    QWidget#topbar, QWidget#statusStrip, QWidget#leftDock {
        background:transparent;border:0;
    }
    QLabel#brand {font-weight:bold;font-size:18px;color:#ECF8FF;}
    QLabel#subtitle {font-size:10px;letter-spacing:2px;color:%s;}
    QLabel#caption, QLabel#hint {font-size:10px;color:#86B3CC;}
    QLabel#sectionHeader {font-weight:bold;color:%s;}
    QLabel#online {color:#39E7A8;font-size:10px;font-weight:bold;}
    QLabel#windowHeading {font-size:11px;color:#ECF8FF;font-weight:bold;}
    QListWidget {background:transparent;border:0;outline:0;padding:8px 2px;}
    QListWidget::item {padding:10px 12px;margin:2px;border-radius:4px;color:#BFE7F8;}
    QListWidget::item:hover {background:#16415C;border-left:2px solid %s;}
    QListWidget::item:selected {background:#155278;border:1px solid %s;color:white;}
    QPushButton {background:#0C2B43;border:1px solid %s;border-radius:4px;
                 padding:5px 9px;min-height:20px;color:#C9EFFF;}
    QPushButton:hover {background:#195276;border-color:%s;color:white;}
    QPushButton:pressed {background:#127FA8;}
    QPushButton#iconNav {background:transparent;border:1px solid transparent;border-radius:3px;
                         padding:5px 12px;min-height:36px;}
    QPushButton#iconNav:hover {background:#123E5B;border-color:%s;}
    QPushButton#iconNav:checked {background:#15577A;border-color:%s;}
    QPushButton#windowCtrl {background:transparent;border:0;padding:0;min-height:0;}
    QPushButton#windowCtrl:hover {background:#235A76;}
    QLineEdit,QPlainTextEdit,QTreeWidget,QComboBox,QTabWidget::pane {
        background:#071728;border:1px solid #285D7C;color:#D6EFFF;
        border-radius:3px;padding:5px;selection-background-color:#19688E;
    }
    QLineEdit:focus {border:1px solid %s;}
    QTabBar::tab {background:#0B263C;color:#A7D8F2;padding:6px 12px;
                  border:1px solid #29617F;}
    QTabBar::tab:selected {background:#12547A;color:#ECFAFF;border-bottom:2px solid %s;}
    QTreeWidget::item {padding:3px;}
    QTreeWidget::item:selected {background:#165578;}
    QHeaderView::section {background:#13334A;color:#A6E8FF;border:0;padding:5px;}
    QMenu {background:#0A2031;border:1px solid %s;padding:5px;}
    QMenu::item {padding:7px 24px;}
    QMenu::item:selected {background:#155A7E;}
    QToolTip {background:#123048;color:white;border:1px solid %s;padding:5px;}
    QProgressBar {background:#0A1D2C;border:1px solid #286889;border-radius:4px;text-align:center;min-height:15px;}
    QProgressBar::chunk {background:%s;border-radius:3px;}
    QCheckBox::indicator {width:16px;height:16px;border:1px solid %s;background:#0A2134;}
    QCheckBox::indicator:checked {background:%s;}
    QSplitter::handle {background:#10405B;width:4px;}
    QScrollBar:vertical {background:#0A1727;width:8px;}
    QScrollBar::handle:vertical {background:#247095;border-radius:3px;}
    """ % (p.background,p.bright,p.accent,p.accent,p.accent,p.edge,p.bright,
           p.accent,p.bright,p.bright,p.accent,p.accent,p.accent,p.bright,
           p.accent,p.bright,p.accent,p.accent)

class RoutedBar(QWidget):
    """QPainter PCB frame, independent of bitmap scaling."""
    def __init__(self,palette,parent=None):
        super().__init__(parent)
        self.palette=palette
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    def set_palette(self,palette):
        self.palette=palette
        self.update()
    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_frame(p,QRectF(self.rect()).adjusted(4,4,-4,-4),self.palette,.85)
        p.end()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOVA CONTROL CENTER — NEXUS NOVA HD V2")
        self.resize(1550,940)
        self.setMinimumSize(960,620)
        self.bus=EventBus(self)
        self.state=self.load_state()
        self.theme_name=self.state.get("theme","ElectroBlueNEON")
        if self.theme_name not in PALETTES:self.theme_name="ElectroBlueNEON"
        self.palette=PALETTES[self.theme_name]
        self._build()
        self.set_theme(self.theme_name)
        if not self.desktop.restore_snapshot(self.state.get("workspace",[])):
            for name in ("demo.terminal","demo.explorer","demo.monitor","demo.controls"):
                self.desktop.open_app(name)
            self.desktop.tileSubWindows()
        self._update_status()
    def _build(self):
        root=QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer=QVBoxLayout(root)
        outer.setContentsMargins(5,4,5,2)
        outer.setSpacing(2)
        self.top=RoutedBar(self.palette)
        self.top.setObjectName("topbar")
        self.top.setFixedHeight(79)
        header=QHBoxLayout(self.top)
        header.setContentsMargins(20,11,15,11)
        header.setSpacing(8)
        self.logo=QLabel()
        self.logo.setPixmap(vector_icon("boxes",self.palette.bright,52).pixmap(48,48))
        header.addWidget(self.logo)
        brand_col=QVBoxLayout()
        brand=QLabel("NOVA CONTROL CENTER   V2")
        brand.setObjectName("brand")
        brand_col.addWidget(brand)
        sub=QLabel("NEXUS NOVA HD  /  ELECTROBLUENEON")
        sub.setObjectName("subtitle")
        brand_col.addWidget(sub)
        header.addLayout(brand_col)
        header.addStretch(1)
        self.nav=[]
        for label,name in (("Bureau","home"),("Système","monitor"),("Réseau","network"),
                           ("Services","layers"),("Sécurité","shield")):
            b=QPushButton(label)
            b.setObjectName("iconNav")
            b.setCheckable(True)
            b.setToolTip("Navigation rapide : "+label)
            b.setIcon(vector_icon(name,self.palette.bright))
            b.setIconSize(QSize(18,18))
            b.clicked.connect(lambda checked=False,k=label:self._nav_action(k))
            self.nav.append((b,name))
            header.addWidget(b)
        self.nav[0][0].setChecked(True)
        for icon,tip,callback in (
            ("grid","Mosaïque",lambda:self.desktop.tileSubWindows()),
            ("layers","Cascade",lambda:self.desktop.cascadeSubWindows()),
            ("save","Sauvegarder",self.save_state),
        ):
            btn=QPushButton()
            btn.setIcon(vector_icon(icon,self.palette.bright))
            btn.setIconSize(QSize(20,20))
            btn.setToolTip(tip)
            btn.setFixedSize(36,34)
            btn.clicked.connect(callback)
            header.addWidget(btn)
            self.nav.append((btn,icon))
        options=QPushButton("◈")
        options.setToolTip("Thèmes et options")
        options.setFixedSize(34,34)
        self.theme_btn=options
        options.setMenu(self.theme_menu())
        header.addWidget(options)
        outer.addWidget(self.top)

        split=QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        self.left=RoutedBar(self.palette)
        self.left.setObjectName("leftDock")
        side=QVBoxLayout(self.left)
        side.setContentsMargins(10,15,10,16)
        side.setSpacing(4)
        head=QLabel("◈  APPLICATIONS")
        head.setObjectName("sectionHeader")
        side.addWidget(head)
        self.catalog=AppShelf(BUILTIN_V2,self.palette)
        self.catalog.launch_requested.connect(self.desktop_open)
        side.addWidget(self.catalog,1)
        line=QLabel("WORKSPACES")
        line.setObjectName("caption")
        side.addWidget(line)
        for name,icon,callback in (
            ("Ajouter une instance","plus",lambda:self._choose_app()),
            ("Enregistrer l'espace","save",self.save_state),
        ):
            btn=QPushButton(name)
            btn.setIcon(vector_icon(icon,self.palette.bright))
            btn.clicked.connect(callback)
            side.addWidget(btn)
            self.nav.append((btn,icon))
        split.addWidget(self.left)
        self.desktop=NexusDesktop(BUILTIN_V2,self.bus,self.palette)
        self.desktop.number_changed.connect(self._update_status)
        split.addWidget(self.desktop)
        split.setStretchFactor(1,1)
        split.setSizes([210,1260])
        self.splitter=split
        outer.addWidget(split,1)

        self.status=RoutedBar(self.palette)
        self.status.setObjectName("statusStrip")
        self.status.setFixedHeight(33)
        line=QHBoxLayout(self.status)
        line.setContentsMargins(17,5,17,5)
        line.setSpacing(13)
        self.status_left=QLabel("●  NOVA CORE  READY")
        self.status_count=QLabel("0 fenêtre")
        self.status_event=QLabel("LOCAL / QT")
        for widget in (self.status_left,self.status_count,self.status_event):
            widget.setFont(QFont("DejaVu Sans",11,QFont.Weight.Normal))
        line.addWidget(self.status_left)
        line.addSpacing(12)
        line.addWidget(self.status_event)
        line.addStretch(1)
        line.addWidget(self.status_count)
        self.status_theme=QLabel(self.theme_name)
        self.status_theme.setFont(QFont("DejaVu Sans",10))
        line.addWidget(self.status_theme)
        outer.addWidget(self.status)

        self.bus.event.connect(self._on_bus)
        command=QAction(self)
        command.setShortcut(QKeySequence("Ctrl+K"))
        command.triggered.connect(self.command_palette)
        self.addAction(command)
    def _nav_action(self,name):
        for btn,icon in self.nav[:5]:
            btn.setChecked(btn.text()==name)
        if name!="Bureau":
            self.status_event.setText("◈ "+name+" : modules de démonstration")
        else:self.status_event.setText("BUREAU / LOCAL")
    def theme_menu(self):
        menu=QMenu(self)
        for name in PALETTES:
            action=menu.addAction(("◉ " if name==self.theme_name else "◯ ")+name)
            action.triggered.connect(lambda checked=False,key=name:self.set_theme(key))
        menu.addSeparator()
        action=menu.addAction("◈  Activer / suspendre animations")
        action.triggered.connect(self.toggle_animation)
        return menu
    def toggle_animation(self):
        self.desktop.effect_enabled=not self.desktop.effect_enabled
        self.status_event.setText("Animations : "+("ON" if self.desktop.effect_enabled else "OFF"))
    def set_theme(self,name):
        if name not in PALETTES:return
        self.theme_name=name
        self.palette=PALETTES[name]
        app=QApplication.instance()
        app.setStyleSheet(qss(self.palette))
        self.top.set_palette(self.palette)
        self.left.set_palette(self.palette)
        self.status.set_palette(self.palette)
        self.desktop.set_palette(self.palette)
        self.catalog.set_palette(self.palette)
        self.logo.setPixmap(vector_icon("boxes",self.palette.bright,52).pixmap(48,48))
        for button,icon in self.nav:
            button.setIcon(vector_icon(icon,self.palette.bright,25))
        self.theme_btn.setMenu(self.theme_menu())
        self.status_theme.setText(name)
    def desktop_open(self,name):
        self.desktop.open_app(name)
        self._update_status()
    def _choose_app(self):
        labels={a.title:a.app_id for a in BUILTIN_V2}
        answer,ok=QInputDialog.getItem(self,"NEXUS / APPLICATIONS","Ouvrir un module Qt :",list(labels),0,False)
        if ok:self.desktop_open(labels[answer])
    def command_palette(self):
        actions={("Ouvrir : "+a.title):lambda n=a.app_id:self.desktop_open(n) for a in BUILTIN_V2}
        actions["Fenêtres : mosaïque"]=self.desktop.tileSubWindows
        actions["Fenêtres : cascade"]=self.desktop.cascadeSubWindows
        actions["Enregistrer l'espace"]=self.save_state
        actions["Thème : ElectroBlueNEON"]=lambda:self.set_theme("ElectroBlueNEON")
        actions["Thème : RougeERROR"]=lambda:self.set_theme("RougeERROR")
        actions["Animations : on / off"]=self.toggle_animation
        choice,ok=QInputDialog.getItem(self,"NEXUS / COMMAND PALETTE","Commande :",list(actions),0,False)
        if ok:actions[choice]()
    def contextMenuEvent(self,event):
        menu=QMenu(self)
        for label,slot in (
            ("⊞  Organiser en mosaïque",self.desktop.tileSubWindows),
            ("▣  Organiser en cascade",self.desktop.cascadeSubWindows),
            ("⊕  Nouvelle application",self._choose_app),
            ("↧  Enregistrer",self.save_state),
            ("⌕  Commandes (Ctrl+K)",self.command_palette),
        ):
            action=menu.addAction(label)
            action.triggered.connect(slot)
        menu.exec(event.globalPos())
    def _on_bus(self,name,payload):
        self.status_event.setText("◈ "+str(name)[:36])
    def _update_status(self,*_):
        if hasattr(self,"status_count"):
            self.status_count.setText(f"{len(self.desktop.subWindowList())} fenêtre(s)")
    def load_state(self):
        try:
            data=json.loads(SETTINGS.read_text(encoding="utf-8"))
            return data if isinstance(data,dict) else {}
        except (ValueError,OSError):return {}
    def save_state(self):
        data={"version":2,"theme":self.theme_name,"workspace":self.desktop.snapshot(),
              "animations":self.desktop.effect_enabled}
        try:
            SETTINGS.parent.mkdir(parents=True,exist_ok=True)
            temp=SETTINGS.with_suffix(".tmp")
            temp.write_text(json.dumps(data,indent=2),encoding="utf-8")
            temp.replace(SETTINGS)
            self.status_event.setText("●  Espace sauvegardé")
        except OSError as exc:
            QMessageBox.warning(self,"Échec de sauvegarde",str(exc))
    def closeEvent(self,event):
        try:self.save_state()
        except Exception:pass
        super().closeEvent(event)

def main():
    app=QApplication(sys.argv)
    app.setApplicationName("NOVA CONTROL CENTER")
    app.setOrganizationName("NOVA")
    window=MainWindow()
    window.show()
    return app.exec()

if __name__=="__main__":
    sys.exit(main())
