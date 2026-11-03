"""Visual-only native Qt showcase modules for NEXUS V2.

No terminal, SFTP or network connection is created. 3D is opt-in and
falls back to a lightweight 2D reactor when Quick3D is unavailable.
"""
import math
import os
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer, QUrl
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QRadialGradient
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QLineEdit, QProgressBar, QCheckBox, QComboBox, QSlider, QPushButton
)
from .v2_skin import THEMES, NeonButton, color, trace, draw_glyph

class HeroPanel(QWidget):
    def __init__(self, context):
        super().__init__()
        v=QVBoxLayout(self)
        v.setContentsMargins(18,15,18,18)
        v.setSpacing(12)
        title=QLabel("NEXUS HD  /  CYBER ELECTRONIC WORKSPACE")
        title.setObjectName("section")
        v.addWidget(title)
        headline=QLabel("NOVA CONTROL CENTER  •  V2")
        headline.setStyleSheet("font-size:21px;font-weight:700;color:#D9F5FF;")
        v.addWidget(headline)
        hint=QLabel("Un bureau natif Qt 6 avec cadres PCB, verre translucide, icônes vectorielles et animations légères.\n"
                    "Les panneaux présentés ici sont des démonstrations graphiques : aucun serveur n'est connecté.")
        hint.setWordWrap(True)
        v.addWidget(hint)
        row=QHBoxLayout()
        for text in ("ELECTROBLUE", "PCB ROUTING", "FULL QT"):
            badge=QLabel("  ◈  "+text+"  ")
            badge.setStyleSheet("background:#103149;border:1px solid #1D9BCC;border-radius:5px;padding:7px;color:#93E6FF;")
            row.addWidget(badge)
        v.addLayout(row)
        v.addStretch()

class RoutingPanel(QWidget):
    def __init__(self, context):
        super().__init__()
        self.palette=THEMES["ElectroBlueNEON"]
        self.setMinimumSize(260,180)
    def apply_theme(self, theme):
        self.palette=theme
        self.update()
    def paintEvent(self, event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height()
        p.setFont(QFont("DejaVu Sans",9,QFont.Weight.Bold))
        p.setPen(color("#B9EAFF"))
        p.drawText(16,25,"NEXUS / ROUTING TOPOLOGY  —  DESIGN PREVIEW")
        nodes=[(.12,.44),(.34,.25),(.59,.40),(.84,.26),(.79,.76),(.44,.79),(.19,.72)]
        pairs=[(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,0),(2,5),(1,5)]
        for a,b in pairs:
            x,y=nodes[a];u,v=nodes[b]
            trace(p,[(x*w,y*h),(u*w,v*h)],self.palette.accent,145,1.4,False)
        for x,y in nodes:
            px,py=x*w,y*h
            p.setBrush(color(self.palette.accent,44))
            p.setPen(QPen(color(self.palette.light,200),1.3))
            p.drawEllipse(QRectF(px-10,py-10,20,20))
            p.drawEllipse(QRectF(px-3,py-3,6,6))
        p.end()

class Reactor2D(QWidget):
    def __init__(self, context):
        super().__init__()
        self.palette=THEMES["ElectroBlueNEON"]
        self.theta=0.0
        self.timer=QTimer(self)
        self.timer.setInterval(70)
        self.timer.timeout.connect(self._step)
        self.timer.start()
    def _step(self):
        if self.isVisible():
            self.theta=(self.theta+1.8)%360
            self.update()
    def apply_theme(self,theme):
        self.palette=theme
        self.update()
    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height()
        p.setPen(color("#B5E8FA"))
        p.setFont(QFont("DejaVu Sans",9,QFont.Weight.DemiBold))
        p.drawText(16,25,"NEXUS REACTOR  /  HOLOGRAPHIC 2D")
        cx,cy=w*.5,h*.54
        r=max(20,min(w,h)*.30)
        glow=QRadialGradient(QPointF(cx,cy),r*1.2)
        glow.setColorAt(0,color(self.palette.accent,85))
        glow.setColorAt(.55,color(self.palette.accent,18))
        glow.setColorAt(1,color(self.palette.accent,0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(cx-r*1.2,cy-r*1.2,r*2.4,r*2.4))
        p.translate(cx,cy)
        p.rotate(self.theta)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(color(self.palette.light,220),2))
        p.drawArc(QRectF(-r,-r,r*2,r*2),35*16,245*16)
        p.setPen(QPen(color(self.palette.accent,120),1.1))
        for angle in range(0,360,15):
            a=math.radians(angle)
            p.drawLine(QPointF(r*.82*math.cos(a),r*.82*math.sin(a)),
                       QPointF(r*math.cos(a),r*math.sin(a)))
        p.rotate(-self.theta*1.55)
        p.drawEllipse(QRectF(-r*.62,-r*.62,r*1.24,r*1.24))
        p.drawEllipse(QRectF(-r*.34,-r*.34,r*.68,r*.68))
        p.end()

class ReactorPanel(QWidget):
    def __init__(self,context):
        super().__init__()
        layout=QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        renderer=None
        self.qt3d_active=False
        if os.environ.get("NOVA_ENABLE_3D") == "1" and os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            try:
                from PySide6.QtQuickWidgets import QQuickWidget
                scene=Path(__file__).with_name("qml")/"reactor.qml"
                if scene.exists():
                    viewer=QQuickWidget()
                    viewer.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
                    viewer.setSource(QUrl.fromLocalFile(str(scene)))
                    if viewer.status() != QQuickWidget.Status.Error:
                        renderer=viewer
                        self.qt3d_active=True
                    else:
                        viewer.deleteLater()
            except (ImportError,RuntimeError,OSError):
                pass
        if renderer is None:
            renderer=Reactor2D(context)
        self.renderer=renderer
        layout.addWidget(renderer)
    def apply_theme(self,theme):
        if hasattr(self.renderer,"apply_theme"):
            self.renderer.apply_theme(theme)

class WidgetPanel(QWidget):
    def __init__(self,context):
        super().__init__()
        self.palette=THEMES["ElectroBlueNEON"]
        v=QVBoxLayout(self)
        v.setContentsMargins(17,14,17,14)
        v.setSpacing(12)
        lab=QLabel("NOVA WIDGET KIT  /  INTERACTIVE UI")
        lab.setObjectName("section")
        v.addWidget(lab)
        row=QHBoxLayout()
        self.buttons=[]
        for title,glyph in (("ACTIVER","power"),("SYNCHRO","refresh"),("ENREGISTRER","save")):
            button=NeonButton(title,glyph,self.palette)
            button.clicked.connect(lambda _, t=title: self.message.setText("ACTION DEMO  /  "+t))
            self.buttons.append(button)
            row.addWidget(button)
        v.addLayout(row)
        field=QLineEdit()
        field.setPlaceholderText("⌕ Rechercher un module…")
        v.addWidget(field)
        self.progress=QProgressBar()
        self.progress.setRange(0,100)
        self.progress.setValue(68)
        v.addWidget(self.progress)
        toggle=QCheckBox("Animer les effets lumineux")
        toggle.setChecked(True)
        v.addWidget(toggle)
        self.message=QLabel("ACTION DEMO  /  READY")
        v.addWidget(self.message)
        v.addStretch(1)
    def apply_theme(self,theme):
        self.palette=theme
        for b in self.buttons:b.apply_theme(theme)
