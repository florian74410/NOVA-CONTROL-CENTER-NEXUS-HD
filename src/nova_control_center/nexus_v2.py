"""NOVA CONTROL CENTER V2 — Full Qt6 CyberPCB desktop.
No connection to remote production services is made by the demo applications.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from dataclasses import dataclass
from PySide6.QtCore import Qt, QObject, Signal, QTimer, QSize
from PySide6.QtGui import QAction,QKeySequence,QFont
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
    QLabel,QSplitter,QMenu,QMessageBox,QInputDialog,QDialog,QLineEdit,QListWidget,
    QListWidgetItem,QFrame)
from .nexus_apps import BUILTIN_APPS, AppContext
from .v2_skin import THEMES, NeonSurface, NeonButton, NovaMark, form_stylesheet, icon
from .v2_workspace import Workspace, AppCatalog

SETTINGS=Path.home()/".config"/"nova-control-center"/"v2.json"

@dataclass(frozen=True)
class AppSpec:
    app_id: str
    title: str
    glyph: str
    factory: object

ICON_IDS=("terminal","folder","settings","activity")
APPS=tuple(AppSpec(d.app_id,d.title,ICON_IDS[n],d.factory)
           for n,d in enumerate(BUILTIN_APPS))

class EventBus(QObject):
    event=Signal(str,object)
    def publish(self,name,payload=None):self.event.emit(name,payload)

class CommandPalette(QDialog):
    def __init__(self,commands,theme,parent=None):
        super().__init__(parent)
        self.setWindowTitle("NEXUS / PALETTE DE COMMANDES")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.setStyleSheet(form_stylesheet(theme))
        self.selected=None
        layout=QVBoxLayout(self)
        self.search=QLineEdit()
        self.search.setPlaceholderText("⌕  Rechercher une commande ou application…")
        layout.addWidget(self.search)
        self.list=QListWidget()
        layout.addWidget(self.list)
        self.entries=commands
        self.search.textChanged.connect(self._filter)
        self.list.itemDoubleClicked.connect(self._choose)
        self._filter("")
        self.search.returnPressed.connect(lambda:self._choose(self.list.currentItem()))
        self.search.setFocus()
    def _filter(self,value):
        self.list.clear()
        for text,callback in self.entries:
            if value.lower() in text.lower():
                item=QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole,len(self.list))
                self.list.addItem(item)
        if self.list.count():self.list.setCurrentRow(0)
    def _choose(self,item):
        if item is None:return
        for label,callback in self.entries:
            if label==item.text():
                self.selected=callback
                self.accept()
                return

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOVA CONTROL CENTER · NEXUS HD V2 — ElectroBlueNEON")
        self.resize(1530,935)
        self.bus=EventBus(self)
        self.context=AppContext(self.bus)
        self.state=self._load_state()
        self.theme_name=self.state.get("theme","ElectroBlueNEON")
        if self.theme_name not in THEMES:self.theme_name="ElectroBlueNEON"
        self.theme=THEMES[self.theme_name]
        self._all_themed=[]
        self._build()
        self.apply_theme(self.theme_name)
        if not self.desktop.restore_snapshot(self.state.get("workspace",[])):
            for app in ("demo.terminal","demo.explorer","demo.controls","demo.events"):
                self.desktop.open_app(app)
            self.desktop.tileSubWindows()
        self._status()
    def _register(self,widget):
        self._all_themed.append(widget)
        return widget
    def _button(self,label,glyph,callback,*,compact=False):
        b=self._register(NeonButton(label,glyph,self.theme,compact=compact))
        b.clicked.connect(callback)
        return b
    def _build(self):
        root=QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer=QVBoxLayout(root)
        outer.setContentsMargins(7,7,7,5)
        outer.setSpacing(5)

        # NAVBAR — icon-first, with a real NEXUS mark and routed glass shell.
        self.header=self._register(NeonSurface(self.theme,cut=17,routing=True,animated=True))
        self.header.setFixedHeight(77)
        header=QHBoxLayout(self.header)
        header.setContentsMargins(14,8,12,9)
        header.setSpacing(8)
        self.mark=self._register(NovaMark(self.theme))
        header.addWidget(self.mark)
        brand_area=QVBoxLayout()
        brand_area.setSpacing(1)
        brand=QLabel("NOVA CONTROL CENTER")
        brand.setObjectName("brand")
        brand_area.addWidget(brand)
        sub=QLabel("NEXUS HD V2  /  ELECTROBLUENEON  /  LINUX WORKSPACE")
        sub.setObjectName("muted")
        sub.setStyleSheet("font-size:9px;letter-spacing:1px;")
        brand_area.addWidget(sub)
        header.addLayout(brand_area)
        header.addStretch()
        for label,glyph,callback in (
            ("", "apps",self._toggle_sidebar),
            ("", "align",lambda:self.desktop.tileSubWindows()),
            ("", "cascade",lambda:self.desktop.cascadeSubWindows()),
            ("", "save",self.save_workspace),
            ("", "search",self.command_palette)):
            b=self._button(label,glyph,callback,compact=True)
            b.setFixedSize(37,36)
            header.addWidget(b)
        self.theme_button=self._button("THÈME","settings",self._theme_menu)
        header.addWidget(self.theme_button)
        self.menu_button=self._button("","grid",self._top_menu,compact=True)
        self.menu_button.setFixedSize(37,36)
        header.addWidget(self.menu_button)
        outer.addWidget(self.header)

        mid=QSplitter(Qt.Orientation.Horizontal)
        mid.setChildrenCollapsible(False)
        self.sidebar=self._register(NeonSurface(self.theme,cut=15,routing=True))
        side=QVBoxLayout(self.sidebar)
        side.setContentsMargins(10,15,10,12)
        side.setSpacing(8)
        sidehead=QLabel("▣   APPLICATIONS")
        sidehead.setObjectName("section")
        side.addWidget(sidehead)
        self.catalog=AppCatalog(APPS)
        self.catalog.setStyleSheet("QListWidget {background:transparent;border:0;} "
            "QListWidget::item {padding:8px 6px;border:1px solid transparent;border-radius:5px;}"
            "QListWidget::item:selected {background:#13496A;border:1px solid #00BFFF;}"
            "QListWidget::item:hover {background:#123650;}")
        self.catalog.launch.connect(self.open_app)
        side.addWidget(self.catalog,1)
        addon=self._button("AJOUTER","plus",self._app_info)
        side.addWidget(addon)
        section=QLabel("WORKSPACES")
        section.setObjectName("section")
        side.addWidget(section)
        save=self._button("Enregistrer","save",self.save_workspace)
        side.addWidget(save)
        self.sidebar.setMinimumWidth(174)
        mid.addWidget(self.sidebar)

        self.desktop=Workspace(APPS,self.context,self.theme)
        self.desktop.number_changed.connect(self._status)
        mid.addWidget(self.desktop)
        mid.setStretchFactor(1,1)
        mid.setSizes([215,1260])
        self.split=mid
        outer.addWidget(mid,1)

        # STATUS — deliberately thin: the text itself is normal 11pt.
        self.footer=self._register(NeonSurface(self.theme,cut=7,routing=False))
        self.footer.setFixedHeight(33)
        row=QHBoxLayout(self.footer)
        row.setContentsMargins(11,1,11,1)
        row.setSpacing(12)
        self.ready=QLabel("●  NOVA CORE READY")
        self.windows=QLabel("")
        self.palette=QLabel("")
        self.note=QLabel("QT 6  ·  LOCAL MODE  ·  NO REMOTE OPERATIONS")
        for widget in (self.ready,self.windows,self.palette,self.note):
            widget.setFont(QFont("DejaVu Sans",11))
            row.addWidget(widget)
        row.insertStretch(1)
        outer.addWidget(self.footer)
        self.bus.event.connect(self._receive)
        shortcut=QAction(self)
        shortcut.setShortcut(QKeySequence("Ctrl+K"))
        shortcut.triggered.connect(self.command_palette)
        self.addAction(shortcut)
    def _toggle_sidebar(self):
        self.sidebar.setVisible(not self.sidebar.isVisible())
    def _top_menu(self):
        m=QMenu(self)
        for label,handler in (
            ("⊞  Ouvrir une application",self.command_palette),
            ("▦  Mosaïque",self.desktop.tileSubWindows),
            ("▣  Cascade",self.desktop.cascadeSubWindows),
            ("↧  Enregistrer la session",self.save_workspace),
            ("ⓘ  À propos",self._about)):
            m.addAction(label,handler)
        m.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))
    def _theme_menu(self):
        m=QMenu(self)
        for name in THEMES:
            m.addAction(("●  " if name==self.theme_name else "○  ")+name,
                        lambda selected=name:self.apply_theme(selected))
        m.exec(self.theme_button.mapToGlobal(self.theme_button.rect().bottomLeft()))
    def open_app(self,app_id):
        self.desktop.open_app(app_id)
        self._status()
    def apply_theme(self,name):
        if name not in THEMES:return
        self.theme_name=name
        self.theme=THEMES[name]
        app=QApplication.instance()
        app.setStyleSheet(form_stylesheet(self.theme))
        self.desktop.set_theme(self.theme)
        for widget in self._all_themed:
            widget.apply_theme(self.theme)
        for item,spec in zip((self.catalog.item(i) for i in range(self.catalog.count())),APPS):
            item.setIcon(icon(spec.glyph,self.theme,23))
        self.setWindowTitle("NOVA CONTROL CENTER · NEXUS HD V2 — "+name)
        self._status()
    def command_palette(self):
        commands=[("OUVRIR  /  "+spec.title,
                   lambda id=spec.app_id:self.open_app(id)) for spec in APPS]
        commands += [
            ("BUREAU  /  Mosaïque",self.desktop.tileSubWindows),
            ("BUREAU  /  Cascade",self.desktop.cascadeSubWindows),
            ("SESSION  /  Enregistrer",self.save_workspace),
            ("THÈME  /  ElectroBlueNEON",lambda:self.apply_theme("ElectroBlueNEON")),
            ("THÈME  /  RougeERROR",lambda:self.apply_theme("RougeERROR")),
        ]
        dialog=CommandPalette(commands,self.theme,self)
        if dialog.exec() and dialog.selected:
            dialog.selected()
    def _status(self,*_args):
        if not hasattr(self,"windows"):return
        self.windows.setText("◈  "+str(len(self.desktop.subWindowList()))+" FENÊTRES")
        self.palette.setText("◆  "+self.theme_name)
    def _receive(self,name,payload):
        self.ready.setText("●  "+name.upper()[:33])
    def _app_info(self):
        QMessageBox.information(self,"NOVA APP MANAGER",
          "Cette V2 est une fondation graphique Full Qt.\n\n"
          "Les applications sont des widgets de démonstration chargés en instances multiples.\n"
          "L'installation de modules externes approuvés sera ajoutée après validation de l'interface.")
    def _about(self):
        QMessageBox.information(self,"NEXUS HD V2",
          "NOVA CONTROL CENTER V2 — CyberPCB / Full Qt 6\n"
          "Bureau multi-fenêtres, verre, pistes électroniques, icônes vectorielles.\n"
          "Mode démonstration hors connexion.")
    def _load_state(self):
        try:
            obj=json.loads(SETTINGS.read_text(encoding="utf-8"))
            return obj if isinstance(obj,dict) else {}
        except (OSError,ValueError):
            return {}
    def save_workspace(self):
        payload={"version":2,"theme":self.theme_name,"workspace":self.desktop.snapshot()}
        try:
            SETTINGS.parent.mkdir(parents=True,exist_ok=True)
            temp=SETTINGS.with_suffix(".tmp")
            temp.write_text(json.dumps(payload,indent=2),encoding="utf-8")
            temp.replace(SETTINGS)
            self.ready.setText("●  SESSION ENREGISTRÉE")
        except OSError as err:
            QMessageBox.warning(self,"Erreur de sauvegarde",str(err))
    def closeEvent(self,event):
        self.save_workspace()
        super().closeEvent(event)

def main():
    app=QApplication(sys.argv)
    app.setApplicationName("NOVA CONTROL CENTER")
    app.setOrganizationName("NOVA")
    win=MainWindow()
    win.show()
    return app.exec()

if __name__=="__main__":
    sys.exit(main())
