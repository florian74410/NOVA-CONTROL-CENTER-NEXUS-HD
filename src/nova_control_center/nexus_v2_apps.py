"""V2 real Qt widgets: application-host demos, never simulated remote connections."""
from __future__ import annotations
import math
import os
from dataclasses import dataclass
from PySide6.QtCore import Qt, QTimer, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QConicalGradient
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QLineEdit, QTabWidget,
    QProgressBar, QCheckBox, QComboBox, QGridLayout, QFrame
)
from .nexus_v2_paint import vector_icon, PALETTES, NexusPanel

@dataclass(frozen=True)
class Descriptor:
    app_id: str
    title: str
    icon: str
    factory: object
    minimum: tuple = (350, 230)

class LocalTerminalDemo(QWidget):
    def __init__(self,bus):
        super().__init__()
        layout=QVBoxLayout(self)
        layout.setContentsMargins(13,8,13,7)
        tabs=QTabWidget()
        text=QPlainTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("DejaVu Sans Mono",10))
        text.setPlainText(
            "NOVA / TERMINAL LAB — OFFLINE PREVIEW\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "No SSH connection is active.\n"
            "The V2 module is an interactive Qt display test.\n\n"
            "nova@local:~$ nova --status\n"
            "NEXUS CORE      READY\n"
            "Qt WINDOW HOST  ACTIVE\n"
            "REMOTE          NOT CONNECTED\n\n"
            "nova@local:~$ ▌"
        )
        tabs.addTab(text,"▣  Session 01")
        second=QPlainTextEdit("NOVA EVENT LOG\nNo network operations executed.")
        second.setReadOnly(True)
        tabs.addTab(second,"◈  Événements")
        layout.addWidget(tabs,1)
        footer=QHBoxLayout()
        status=QLabel("● LOCAL DEMO  |  Aucun serveur connecté")
        status.setObjectName("hint")
        footer.addWidget(status,1)
        send=QPushButton("↻  Événement de test")
        send.clicked.connect(lambda:bus.publish("demo.file.changed",{"path":"/demo/config.json"}))
        footer.addWidget(send)
        layout.addLayout(footer)

class ExplorerDemo(QWidget):
    def __init__(self,bus):
        super().__init__()
        layout=QVBoxLayout(self)
        layout.setContentsMargins(11,8,11,7)
        row=QHBoxLayout()
        for name,icon in (("Retour","←"),("Avancer","→"),("Monter","↑")):
            b=QPushButton(icon)
            b.setToolTip(name)
            b.setFixedWidth(31)
            row.addWidget(b)
        address=QLineEdit("/demo/nova")
        address.setReadOnly(True)
        row.addWidget(address,1)
        layout.addLayout(row)
        tree=QTreeWidget()
        tree.setHeaderLabels(["Nom","Type","État"])
        root=QTreeWidgetItem(["NOVA / DEMO","Dossier","LOCAL"])
        folders=["src","assets","themes","docs","config.json"]
        for name in folders:
            root.addChild(QTreeWidgetItem([name,"JSON" if name.endswith(".json") else "Dossier","Exemple"]))
        tree.addTopLevelItem(root)
        tree.expandAll()
        layout.addWidget(tree,1)
        self.status=QLabel("● Arborescence de démonstration — pas de connexion SFTP")
        self.status.setObjectName("hint")
        layout.addWidget(self.status)
        bus.event.connect(self.on_event)
    def on_event(self,name,payload):
        if name=="demo.file.changed":
            self.status.setText("◈ Mise à jour reçue : "+str(payload.get("path","?")))

class Gauge(QWidget):
    def __init__(self,name,value=0,parent=None):
        super().__init__(parent)
        self.name=name
        self.value=value
        self.setMinimumSize(90,100)
    def set_value(self,value):
        self.value=max(0,min(100,int(value)))
        self.update()
    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height()
        s=max(1,min(w,h)-16)
        rect=QRectF((w-s)/2,(h-s)/2,s,s)
        p.setPen(QPen(QColor("#143A5C"),8))
        p.drawArc(rect,30*16,300*16)
        p.setPen(QPen(QColor("#0AD5FF"),7))
        p.drawArc(rect,(30+300*(1-self.value/100))*16,300*self.value/100*16)
        p.setPen(QColor("#BCEBFF"))
        p.setFont(QFont("DejaVu Sans",9,QFont.Weight.Bold))
        p.drawText(QRectF(0,h*.31,w,h*.22),Qt.AlignmentFlag.AlignCenter,self.name)
        p.setFont(QFont("DejaVu Sans",17,QFont.Weight.Bold))
        p.drawText(QRectF(0,h*.48,w,h*.28),Qt.AlignmentFlag.AlignCenter,f"{self.value}%")
        p.end()

class LocalMonitorDemo(QWidget):
    def __init__(self,bus):
        super().__init__()
        layout=QVBoxLayout(self)
        layout.setContentsMargins(12,8,12,9)
        head=QHBoxLayout()
        label=QLabel("◉  LOCAL SYSTEM / LINUX")
        label.setObjectName("sectionHeader")
        head.addWidget(label)
        head.addStretch()
        tag=QLabel("● LOCAL")
        tag.setObjectName("online")
        head.addWidget(tag)
        layout.addLayout(head)
        self.cpu=Gauge("CPU")
        self.mem=Gauge("RAM")
        self.disk=Gauge("DISK")
        group=QHBoxLayout()
        for gauge in (self.cpu,self.mem,self.disk):
            group.addWidget(gauge,1)
        layout.addLayout(group,1)
        self.details=QLabel("Collecte locale disponible sur Linux via /proc.")
        self.details.setObjectName("hint")
        layout.addWidget(self.details)
        self._last_cpu=None
        self.timer=QTimer(self)
        self.timer.setInterval(1800)
        self.timer.timeout.connect(self.update_readings)
        self.timer.start()
        self.update_readings()
    def update_readings(self):
        try:
            with open("/proc/stat",encoding="ascii") as f:
                values=[int(n) for n in f.readline().split()[1:]]
            total=sum(values)
            idle=values[3]+(values[4] if len(values)>4 else 0)
            if self._last_cpu:
                prior_total,prior_idle=self._last_cpu
                delta=max(1,total-prior_total)
                self.cpu.set_value(100*(1-(idle-prior_idle)/delta))
            self._last_cpu=(total,idle)
        except (OSError,ValueError,IndexError):
            pass
        try:
            memory={}
            with open("/proc/meminfo",encoding="ascii") as f:
                for line in f:
                    k,_,v=line.partition(":")
                    memory[k]=int(v.strip().split()[0])
            total=memory["MemTotal"]
            available=memory["MemAvailable"]
            self.mem.set_value(100*(total-available)/max(1,total))
        except (OSError,ValueError,KeyError,IndexError):
            pass
        try:
            stat=os.statvfs(os.path.expanduser("~"))
            total=stat.f_blocks*stat.f_frsize
            free=stat.f_bavail*stat.f_frsize
            self.disk.set_value(100*(total-free)/max(1,total))
        except (OSError,ValueError):
            pass

class WidgetsDemo(QWidget):
    def __init__(self,bus):
        super().__init__()
        layout=QVBoxLayout(self)
        layout.setContentsMargins(15,10,15,10)
        heading=QLabel("◈  NEXUS UI COMPONENT LAB")
        heading.setObjectName("sectionHeader")
        layout.addWidget(heading)
        layout.addWidget(QLabel("Champ de recherche"))
        row=QHBoxLayout()
        field=QLineEdit()
        field.setPlaceholderText("Rechercher une application ou une commande...")
        row.addWidget(field,1)
        row.addWidget(QPushButton("⌕"))
        layout.addLayout(row)
        layout.addWidget(QLabel("Paramètres de rendu"))
        layout.addWidget(QCheckBox("Animations néon activées"))
        layout.addWidget(QCheckBox("Décorations PCB et transparence"))
        selector=QComboBox()
        selector.addItems(["ElectroBlueNEON","RougeERROR"])
        layout.addWidget(selector)
        progress=QProgressBar()
        progress.setValue(72)
        layout.addWidget(progress)
        row=QHBoxLayout()
        row.addWidget(QPushButton("✓ Appliquer"))
        row.addWidget(QPushButton("↻ Réinitialiser"))
        layout.addLayout(row)
        layout.addStretch(1)

BUILTIN_V2 = [
    Descriptor("demo.terminal","Terminal / SSH","terminal",LocalTerminalDemo),
    Descriptor("demo.explorer","Fichiers / SFTP","folder",ExplorerDemo),
    Descriptor("demo.monitor","Moniteur système","monitor",LocalMonitorDemo),
    Descriptor("demo.controls","NEXUS Widget Lab","settings",WidgetsDemo),
]
