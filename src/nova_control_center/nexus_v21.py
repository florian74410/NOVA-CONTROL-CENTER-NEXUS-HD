"""NOVA CONTROL CENTER 2.1 — clean frameless Qt shell without fake applications."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QObject, QSize, QRectF, QPoint, QEvent, QTimer
from PySide6.QtGui import QFont, QKeySequence, QAction, QPainter, QIcon, QMovie
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QHBoxLayout,
    QVBoxLayout, QSplitter, QMenu, QMessageBox, QInputDialog, QFrame, QWidgetAction
)
from .nexus_theme import PALETTES
from .nexus_v2_paint import vector_icon, draw_frame
from .nexus_v2_desktop import AppShelf, NexusDesktop
from .nexus_v21_effects import NotificationLayer, PulseIndicator
from .app_registry import ApplicationRegistry, discover_manifests
from .control_panels import ControlSettingsDialog, ControlSessionsDialog
from .core_settings import PreferencesStore
from .core_logs import LogStore
from .core_sessions import SessionManager
from .core_dialogs import LogsDialog, CorePreferencesDialog, UnlockDialog

SETTINGS = Path.home()/".config"/"nova-control-center"/"v21.json"
INSTALLED = Path.home()/".local"/"share"/"nova-control-center"/"Applications"/"Installed"

class EventBus(QObject):
    event=Signal(str,object)
    def publish(self,name,data=None):
        self.event.emit(name,data)

def qss(p):
    accent=p.accent
    light=p.bright
    return """
    QWidget {color:#D9EDFA;font-family:'DejaVu Sans','Noto Sans',sans-serif;font-size:12px;}
    QWidget#root {background:%s;}
    QWidget#topbar, QWidget#statusStrip, QWidget#leftDock {background:transparent;border:0;}
    QLabel#brand {font-weight:bold;font-size:18px;color:#ECF8FF;}
    QLabel#subtitle {font-size:10px;letter-spacing:2px;color:%s;}
    QLabel#hint, QLabel#caption {color:#91B9D0;font-size:11px;}
    QLabel#sectionHeader {font-weight:bold;color:%s;}
    QLabel#windowHeading {font-weight:bold;color:#DCEEFF;}
    QLabel#online {color:#28E1AC;}
    QListWidget {background:transparent;border:0;outline:0;padding:6px 2px;}
    QListWidget::item {padding:11px 12px;margin:2px;color:#C9E9F7;}
    QListWidget::item:hover {background:#174562;border-left:2px solid %s;}
    QListWidget::item:selected {background:#134967;border:1px solid %s;}
    QPushButton {background:#0B283E;border:1px solid %s;border-radius:4px;
                 padding:5px 9px;min-height:22px;color:#D8EDFF;}
    QPushButton:hover {background:#174463;border-color:%s;color:white;}
    QPushButton:pressed {background:#126589;}
    QPushButton#iconNav {background:transparent;border:1px solid transparent;
                         padding:6px 10px;min-height:33px;}
    QPushButton#iconNav:hover {background:#113B56;border-color:%s;}
    QPushButton#iconNav:checked {background:#164766;border-bottom:2px solid %s;}
    QPushButton#windowCtrl {background:transparent;border:0;padding:0;min-height:0;}
    QPushButton#windowCtrl:hover {background:#185473;}
    QMenu {background:#092035;border:1px solid %s;padding:6px;}
    QMenu::item {padding:9px 28px;border-radius:3px;}
    QMenu::item:selected {background:#175171;}
    QMenu::separator {height:1px;background:#245773;margin:5px 10px;}
    QToolTip {background:#10283C;color:#E4F7FF;border:1px solid %s;padding:5px;}
    QLineEdit, QComboBox {background:#0A1C2F;border:1px solid #28628B;
                          border-radius:4px;padding:7px;color:#E8F7FF;}
    QSplitter::handle {background:#163F59;width:4px;}
    QScrollBar:vertical {background:#071424;width:8px;}
    QScrollBar::handle:vertical {background:#2578A0;border-radius:4px;}
    """ % (p.background, light, accent, accent, light, p.edge, light,
           accent, light, p.edge, accent)

class RoutedBar(QWidget):
    def __init__(self,palette,parent=None,draggable=False):
        super().__init__(parent)
        self.palette=palette
        self.draggable=draggable
        self._manual_offset=None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    def set_palette(self,p):
        self.palette=p
        self.update()
    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_frame(painter,QRectF(self.rect()).adjusted(4,4,-4,-4),self.palette,.87)
        painter.end()
    def mousePressEvent(self,event):
        if self.draggable and event.button()==Qt.MouseButton.LeftButton:
            host=self.window()
            if host.isMaximized():return
            if host.windowHandle() is not None and host.windowHandle().startSystemMove():
                event.accept()
                return
            self._manual_offset=event.globalPosition().toPoint()-host.pos()
            event.accept()
            return
        super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        if self._manual_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint()-self._manual_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self,event):
        self._manual_offset=None
        super().mouseReleaseEvent(event)
    def mouseDoubleClickEvent(self,event):
        if self.draggable:
            self.window().toggle_maximized()
            event.accept()
        else:super().mouseDoubleClickEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOVA CONTROL CENTER — NEXUS HD 2.3")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(1480,890)
        self.setMinimumSize(920,550)
        self.bus=EventBus(self)
        self.preferences_store=PreferencesStore()
        self.preferences=self.preferences_store.load()
        self.log_store=LogStore()
        self.session_manager=SessionManager()
        self.registry=ApplicationRegistry()  # zero fake modules
        self.state=self.load_state()
        self.theme_name=self.state.get("theme","ElectroBlueNEON")
        if self.theme_name not in PALETTES:
            self.theme_name="ElectroBlueNEON"
        self.palette=PALETTES[self.theme_name]
        self._build()
        self.set_theme(self.theme_name)
        self.desktop.effect_enabled=bool(self.state.get("animations",True))
        from PySide6.QtCore import QSettings
        if str(QSettings("NOVA","ControlCenter").value("restore_workspace","true")).lower()=="true":
            self.desktop.restore_snapshot(self.state.get("workspace",[]))
        self._update_status()
        self.log_store.write("AUDIT","core","session.started","Session NOVA initialisée",
                             self.session_manager.session.session_id)
        self._idle_timer=QTimer(self)
        self._idle_timer.setInterval(15000)
        self._idle_timer.timeout.connect(self._check_idle_lock)
        self._idle_timer.start()
        QApplication.instance().installEventFilter(self)
        if self.session_manager.has_pin():
            self.session_manager.lock()
            QTimer.singleShot(0,self._unlock_or_exit)
    def _build(self):
        root=QWidget(self)
        root.setObjectName("root")
        root.installEventFilter(self)
        self.setCentralWidget(root)
        column=QVBoxLayout(root)
        column.setContentsMargins(5,4,5,3)
        column.setSpacing(3)

        self.top=RoutedBar(self.palette,draggable=True)
        self.top.setObjectName("topbar")
        self.top.setFixedHeight(76)
        head=QHBoxLayout(self.top)
        head.setContentsMargins(19,10,14,10)
        head.setSpacing(7)
        self.logo=QLabel()
        self.logo.setPixmap(vector_icon("boxes",self.palette.bright,50).pixmap(46,46))
        head.addWidget(self.logo)
        titles=QVBoxLayout()
        titles.setSpacing(0)
        self.brand=QLabel("NOVA CONTROL CENTER")
        self.brand.setObjectName("brand")
        titles.addWidget(self.brand)
        self.subtitle=QLabel("NEXUS HD 2.3  /  ELECTROBLUENEON")
        self.subtitle.setObjectName("subtitle")
        titles.addWidget(self.subtitle)
        head.addLayout(titles)
        head.addStretch(1)
        self.header_buttons=[]
        for label,ico,action in (
            ("Bureau","home",self.show_workspace),
            ("Applications","apps",self.show_catalog),
            ("Espaces","layers",self.show_workspaces),
            ("Paramètres","settings",self.show_settings),
            ("Sessions","shield",self.show_sessions),
            ("Journaux","list",self.show_logs),
        ):
            btn=QPushButton(label)
            btn.setObjectName("iconNav")
            btn.setIcon(vector_icon(ico,self.palette.bright))
            btn.setIconSize(QSize(19,19))
            btn.clicked.connect(action)
            self.header_buttons.append((btn,ico))
            head.addWidget(btn)
        for label,ico,action in (
            ("Disposition mosaïque","grid",self.tile_windows),
            ("Disposition cascade","layers",self.cascade_windows),
            ("Sauvegarder","save",self.save_state),
        ):
            btn=QPushButton()
            btn.setToolTip(label)
            btn.setIcon(vector_icon(ico,self.palette.bright,22))
            btn.setFixedSize(32,32)
            btn.clicked.connect(action)
            self.header_buttons.append((btn,ico))
            head.addWidget(btn)
        menu_button=QPushButton()
        menu_button.setToolTip("Menu principal")
        menu_button.setIcon(vector_icon("settings",self.palette.bright,22))
        menu_button.setFixedSize(32,32)
        menu_button.setMenu(self.make_menu())
        self.menu_button=menu_button
        head.addWidget(menu_button)
        for ico,tip,action in (
            ("minimize","Réduire NOVA",self.showMinimized),
            ("maximize","Agrandir / restaurer NOVA",self.toggle_maximized),
            ("close","Quitter NOVA",self.close),
        ):
            b=QPushButton()
            b.setObjectName("windowCtrl")
            b.setIcon(vector_icon(ico,self.palette.bright))
            b.setIconSize(QSize(17,17))
            b.setFixedSize(27,27)
            b.setToolTip(tip)
            b.clicked.connect(action)
            head.addWidget(b)
            self.header_buttons.append((b,ico))
        column.addWidget(self.top)

        splitter=QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.sidebar=RoutedBar(self.palette)
        self.sidebar.setObjectName("leftDock")
        left=QVBoxLayout(self.sidebar)
        left.setContentsMargins(10,16,10,16)
        left.setSpacing(8)
        heading=QLabel("◈  NOVA / APPLICATIONS")
        heading.setObjectName("sectionHeader")
        left.addWidget(heading)
        self.catalog=AppShelf(self.registry.descriptors(),self.palette)
        self.catalog.launch_requested.connect(self.open_application)
        self.catalog.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.catalog.customContextMenuRequested.connect(
            lambda pos: self.make_menu().exec(self.catalog.mapToGlobal(pos))
        )
        left.addWidget(self.catalog,1)
        self.empty_catalog=QLabel("Aucun module installé.\n\nAjoute une application Qt\npour la voir ici.")
        self.empty_catalog.setWordWrap(True)
        self.empty_catalog.setObjectName("hint")
        self.empty_catalog.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self.empty_catalog)
        for text,ico,slot in (
            ("Bibliothèque","apps",self.show_catalog),
            ("Notifications","bell",self.show_notifications),
            ("Sessions & Connexions","shield",self.show_sessions),
            ("Logs SQLite","list",self.show_logs),
            ("Verrouiller","shield",self.lock_session),
            ("Espaces de travail","layers",self.show_workspaces),
            ("Préférences","settings",self.show_settings),
        ):
            btn=QPushButton(text)
            btn.setIcon(vector_icon(ico,self.palette.bright))
            btn.clicked.connect(slot)
            left.addWidget(btn)
            self.header_buttons.append((btn,ico))
        splitter.addWidget(self.sidebar)
        self.desktop=NexusDesktop(self.registry.descriptors(),self.bus,self.palette)
        self.desktop.number_changed.connect(self._update_status)
        self.desktop.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.desktop.customContextMenuRequested.connect(
            lambda pos: self.make_menu().exec(self.desktop.mapToGlobal(pos))
        )
        splitter.addWidget(self.desktop)
        splitter.setStretchFactor(1,1)
        splitter.setSizes([223,1200])
        self.splitter=splitter
        column.addWidget(splitter,1)

        self.status=RoutedBar(self.palette)
        self.status.setObjectName("statusStrip")
        self.status.setFixedHeight(31)
        row=QHBoxLayout(self.status)
        row.setContentsMargins(17,3,17,3)
        row.setSpacing(11)
        self.indicator=PulseIndicator(self.palette)
        row.addWidget(self.indicator)
        self.status_core=QLabel("NOVA CORE / READY")
        self.status_info=QLabel("0 modules actifs")
        self.status_windows=QLabel("0 fenêtres")
        for label in (self.status_core,self.status_info,self.status_windows):
            label.setFont(QFont("DejaVu Sans",11,QFont.Weight.Normal))
        row.addWidget(self.status_core)
        row.addWidget(self.status_info)
        row.addStretch()
        row.addWidget(self.status_windows)
        column.addWidget(self.status)

        self.notifications=NotificationLayer(root,self.palette)
        self.bus.event.connect(self._on_event)
        action=QAction(self)
        action.setShortcut(QKeySequence("Ctrl+K"))
        action.triggered.connect(self.command_palette)
        self.addAction(action)
        self.status_info.setText("Aucune application tierce chargée")

    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.KeyPress,
                            QEvent.Type.Wheel,QEvent.Type.TouchBegin):
            if hasattr(self,"session_manager"):
                self.session_manager.touch()
        if obj is self.centralWidget() and event.type()==QEvent.Type.MouseButtonPress:
            pos=event.position().toPoint()
            rect=obj.rect()
            margin=8
            edges=Qt.Edge(0)
            if pos.x()<margin:edges|=Qt.Edge.LeftEdge
            if pos.x()>rect.width()-margin:edges|=Qt.Edge.RightEdge
            if pos.y()<margin:edges|=Qt.Edge.TopEdge
            if pos.y()>rect.height()-margin:edges|=Qt.Edge.BottomEdge
            if edges and event.button()==Qt.MouseButton.LeftButton and not self.isMaximized():
                handle=self.windowHandle()
                if handle is not None and handle.startSystemResize(edges):
                    return True
        return super().eventFilter(obj,event)
    def toggle_maximized(self):
        if self.isMaximized():self.showNormal()
        else:self.showMaximized()
    def open_application(self,app_id):
        if app_id not in self.desktop.registry:return
        self.desktop.open_app(app_id)
        self._update_status()
    def tile_windows(self):
        self.desktop.tileSubWindows()
    def cascade_windows(self):
        self.desktop.cascadeSubWindows()
    def show_workspace(self):
        self.notifications.add("Bureau NOVA prêt — dépose ici tes applications Qt.","success")
    def show_catalog(self):
        found=discover_manifests(INSTALLED)
        self.notifications.add(f"Applications détectées : {len(found)}. Activation manuelle requise.","info")
    def show_workspaces(self):
        self.notifications.add("Espace actuel sauvegardable depuis le menu NEXUS.","info")
    def show_settings(self):
        dialog=ControlSettingsDialog(self.palette,self)
        dialog.applied.connect(self.apply_settings)
        dialog.exec()

    def apply_settings(self,data):
        self.set_theme(data.get("theme",self.theme_name))
        self.desktop.effect_enabled=bool(data.get("animations",True))
        if self.desktop.effect_enabled:self.indicator.timer.start()
        else:self.indicator.timer.stop()
        width=int(data.get("sidebar_width",223))
        self.splitter.setSizes([width,max(200,self.splitter.width()-width)])
        self.notifications.add("Paramètres NOVA enregistrés.","success")

    def show_sessions(self):
        if self.session_manager.session.locked:
            self._unlock_or_exit()
            if self.session_manager.session.locked:return
        self.log_store.write("AUDIT","sessions","profiles.opened","Portail connexions ouvert",
                             self.session_manager.session.session_id)
        dialog=ControlSessionsDialog(self.palette,self)
        dialog.ssh_verified.connect(
            lambda name,ok:self.notifications.add(
                f"SSH {name} : "+("connexion vérifiée" if ok else "échec de connexion"),
                "success" if ok else "error"))
        dialog.exec()
    def show_logs(self):
        dialog=LogsDialog(self.palette,self.log_store,self.preferences,self)
        dialog.exec()

    def show_core_preferences(self):
        dialog=CorePreferencesDialog(self.palette,self.preferences_store,
            self.preferences,self.session_manager,self._core_prefs_updated,self)
        dialog.exec()

    def _core_prefs_updated(self):
        self.preferences=self.preferences_store.load()
        self.log_store.prune(self.preferences.log_retention_days,self.preferences.log_max_records)
        self.log_store.write("AUDIT","core","preferences.updated","Préférences Core enregistrées",
                             self.session_manager.session.session_id)
        self.notifications.add("Configuration Core enregistrée.","success")

    def lock_session(self):
        if not self.session_manager.has_pin():
            self.notifications.add("Configure un PIN dans Configuration Core avant de verrouiller.","warning")
            return
        if self.session_manager.lock():
            self.log_store.write("AUDIT","security","session.locked","Verrouillage manuel",
                                 self.session_manager.session.session_id)
            self._unlock_or_exit()

    def _unlock_or_exit(self):
        if not self.session_manager.session.locked:return
        dialog=UnlockDialog(self.palette,self.session_manager,self)
        if dialog.exec()==dialog.DialogCode.Accepted:
            self.log_store.write("AUDIT","security","session.unlocked","Session déverrouillée",
                                 self.session_manager.session.session_id)
        else:
            self.close()

    def _check_idle_lock(self):
        if self.preferences.lock_after_minutes and self.session_manager.auto_lock_due(
              self.preferences.lock_after_minutes):
            self.log_store.write("AUDIT","security","session.auto_locked",
                "Verrouillage après inactivité",self.session_manager.session.session_id)
            self.session_manager.lock()
            self._unlock_or_exit()

    def show_notifications(self):
        self.notifications.add("Bienvenue dans le système de notifications NEXUS.","success")
    def set_theme(self,key):
        if key not in PALETTES:return
        self.theme_name=key
        self.palette=PALETTES[key]
        QApplication.instance().setStyleSheet(qss(self.palette))
        self.top.set_palette(self.palette)
        self.sidebar.set_palette(self.palette)
        self.status.set_palette(self.palette)
        self.desktop.set_palette(self.palette)
        self.catalog.set_palette(self.palette)
        self.notifications.set_palette(self.palette)
        self.indicator.set_palette(self.palette)
        self.logo.setPixmap(vector_icon("boxes",self.palette.bright,50).pixmap(46,46))
        for b,icon in self.header_buttons:
            b.setIcon(vector_icon(icon,self.palette.bright))
        self.menu_button.setMenu(self.make_menu())
        self.subtitle.setText("NEXUS HD 2.1  /  "+key.upper())
    def make_menu(self):
        menu=QMenu(self)
        # Prefer original transparent GIF in the menu header; CSS fallback remains usable.
        animated=(Path(__file__).resolve().parents[2] /
                    "Assets"/"Generated"/"Animations"/self.theme_name/"pcb.gif")
        if animated.is_file():
            action_header=QWidgetAction(menu)
            header=QWidget(menu)
            row=QHBoxLayout(header)
            row.setContentsMargins(12,3,12,3)
            icon=QLabel(header)
            movie=QMovie(str(animated),parent=icon)
            movie.setScaledSize(QSize(46,46))
            icon.setMovie(movie)
            movie.start()
            row.addWidget(icon)
            title=QLabel("NEXUS // "+self.theme_name)
            title.setObjectName("sectionHeader")
            row.addWidget(title)
            action_header.setDefaultWidget(header)
            menu.addAction(action_header)
            menu.addSeparator()
        actions=[
            ("⌂  Bureau",self.show_workspace),
            ("⚙  Paramètres",self.show_settings),
            ("◈  Sessions / Connexions",self.show_sessions),
            ("▤  Logs SQLite",self.show_logs),
            ("⚙  Configuration du Core",self.show_core_preferences),
            ("◈  Verrouiller NOVA",self.lock_session),
            ("▦  Bibliothèque d'applications",self.show_catalog),
            ("▣  Disposition mosaïque",self.tile_windows),
            ("▤  Disposition cascade",self.cascade_windows),
            ("↧  Sauvegarder l'espace",self.save_state),
            (None,None),
            ("◉  ElectroBlueNEON",lambda:self.set_theme("ElectroBlueNEON")),
            ("◉  RougeERROR",lambda:self.set_theme("RougeERROR")),
            ("◈  Activer / couper les animations",self.toggle_animations),
            (None,None),
            ("✓  Tester une notification",lambda:self.notifications.add("Opération terminée.","success")),
            ("!  Tester une erreur",lambda:self.notifications.add("Erreur de démonstration visuelle.","error")),
            ("ⓘ  À propos",self.show_about),
        ]
        for label,fn in actions:
            if label is None:menu.addSeparator()
            else:
                action=menu.addAction(label)
                action.triggered.connect(fn)
        return menu
    def toggle_animations(self):
        self.desktop.effect_enabled=not self.desktop.effect_enabled
        if self.desktop.effect_enabled:self.indicator.timer.start()
        else:self.indicator.timer.stop()
        self.notifications.add("Animations "+("activées" if self.desktop.effect_enabled else "désactivées"),"info")
    def show_about(self):
        QMessageBox.information(self,"NOVA CONTROL CENTER",
            "NEXUS HD 2.1 — Framework Full Qt natif.\n"
            "Aucune application fictive n'est chargée.\n"
            "Les applications devront être installées et autorisées séparément.")
    def command_palette(self):
        actions={
            "Ouvrir bibliothèque":self.show_catalog,
            "Paramètres NOVA":self.show_settings,
            "Sessions / Connexions":self.show_sessions,
            "Logs SQLite":self.show_logs,
            "Configuration du Core":self.show_core_preferences,
            "Verrouiller la session":self.lock_session,
            "Tester notification succès":lambda:self.notifications.add("Succès","success"),
            "Tester notification erreur":lambda:self.notifications.add("Erreur","error"),
            "Tester notification avertissement":lambda:self.notifications.add("Attention","warning"),
            "Sauvegarder espace":self.save_state,
            "Thème ElectroBlueNEON":lambda:self.set_theme("ElectroBlueNEON"),
            "Thème RougeERROR":lambda:self.set_theme("RougeERROR"),
            "Animations ON / OFF":self.toggle_animations,
        }
        option,ok=QInputDialog.getItem(self,"NEXUS COMMAND PALETTE","Action",list(actions),0,False)
        if ok:actions[option]()
    def contextMenuEvent(self,event):
        menu=self.make_menu()
        menu.exec(event.globalPos())
    def _on_event(self,name,payload):
        self.status_info.setText(str(name)[:45])
        if self.preferences.audit_enabled:
            self.log_store.write("INFO","event_bus",str(name),"Événement NOVA",
                                 self.session_manager.session.session_id)
    def _update_status(self,*_):
        if hasattr(self,"status_windows"):
            self.status_windows.setText(f"{len(self.desktop.subWindowList())} fenêtres")
    def load_state(self):
        try:
            value=json.loads(SETTINGS.read_text(encoding="utf-8"))
            return value if isinstance(value,dict) else {}
        except (ValueError,OSError):return {}
    def save_state(self):
        data={"version":"2.1","theme":self.theme_name,
              "workspace":self.desktop.snapshot(),"animations":self.desktop.effect_enabled}
        try:
            SETTINGS.parent.mkdir(parents=True,exist_ok=True)
            tmp=SETTINGS.with_suffix(".tmp")
            tmp.write_text(json.dumps(data,indent=2),encoding="utf-8")
            tmp.replace(SETTINGS)
            self.status_info.setText("Espace sauvegardé")
        except OSError as exc:
            QMessageBox.warning(self,"Sauvegarde impossible",str(exc))
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,"notifications"):self.notifications.rearrange()
    def closeEvent(self,event):
        if not getattr(self,"_core_closed",False):
            self._core_closed=True
            self._idle_timer.stop()
            QApplication.instance().removeEventFilter(self)
            self.log_store.write("AUDIT","core","session.ended","Fermeture du portail",
                                 self.session_manager.session.session_id)
            self.save_state()
            self.log_store.close()
        super().closeEvent(event)

def main():
    app=QApplication(sys.argv)
    app.setApplicationName("NOVA CONTROL CENTER")
    app.setOrganizationName("NOVA")
    mainwindow=MainWindow()
    mainwindow.show()
    return app.exec()

if __name__=="__main__":
    sys.exit(main())
