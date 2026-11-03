"""NEXUS V2 — lightweight scalable cyber-electronic vector skin for Qt6."""
from __future__ import annotations
from dataclasses import dataclass
import math
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer, Signal
from PySide6.QtGui import (QColor, QPainter, QPen, QBrush, QPainterPath,
    QLinearGradient, QRadialGradient, QFont, QFontMetrics, QPolygonF, QIcon, QPixmap)
from PySide6.QtWidgets import QWidget, QPushButton, QFrame, QLabel, QApplication

@dataclass(frozen=True)
class Colors:
    name: str
    bg: str
    panel: str
    accent: str
    light: str
    border: str
    subtle: str

THEMES = {
    "ElectroBlueNEON": Colors("ElectroBlueNEON", "#04101F", "#091D34",
        "#00CFFF", "#82EDFF", "#17658B", "#497B9A"),
    "RougeERROR": Colors("RougeERROR", "#130811", "#29121E",
        "#FF294F", "#FFA0AD", "#8D2440", "#AF5262"),
}

def color(value, a=255):
    c = QColor(value)
    c.setAlpha(max(0, min(255, int(a))))
    return c

def bevel_rect(rect, cut=12):
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    cut = min(cut, w / 4, h / 4)
    path = QPainterPath()
    path.moveTo(x + cut, y)
    path.lineTo(x + w - cut, y)
    path.lineTo(x + w, y + cut)
    path.lineTo(x + w, y + h - cut)
    path.lineTo(x + w - cut, y + h)
    path.lineTo(x + cut, y + h)
    path.lineTo(x, y + h - cut)
    path.lineTo(x, y + cut)
    path.closeSubpath()
    return path

def trace(p, points, accent, alpha=105, thickness=1.2, via=True):
    if len(points) < 2:
        return
    pen = QPen(color(accent, alpha), thickness)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    for a, b in zip(points[:-1], points[1:]):
        p.drawLine(QPointF(*a), QPointF(*b))
    if via:
        x, y = points[-1]
        p.setBrush(color(accent, 45))
        p.drawEllipse(QPointF(x, y), 2.6, 2.6)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(x, y), 1.1, 1.1)

def circuit_border(p, r, theme, strength=1.0, phase=0.0):
    x,y,w,h = r.x(),r.y(),r.width(),r.height()
    if w < 50 or h < 40:
        return
    a = theme.accent
    for i in range(3):
        d = i * 8
        # parallel, fixed-width PCB copper traces; no triangular artifacts
        trace(p, [(x+28+d,y+5+d),(x+75+d,y+5+d),
                  (x+87+d,y+17+d),(min(x+w*.41,x+155+d),y+17+d)],
              a, int((76-i*20)*strength), 1.15,True)
        trace(p, [(x+w-30-d,y+h-5-d),(x+w-82-d,y+h-5-d),
                  (x+w-95-d,y+h-18-d),(max(x+w*.64,x+w-165-d),y+h-18-d)],
              a, int((82-i*20)*strength), 1.15, True)
    # moving electric packet on the top routed conductor
    span = max(1.0, w-190)
    sx = x + 92 + ((phase % 1.0) * span)
    p.setPen(QPen(color(theme.light, 80), 4.2))
    p.drawLine(QPointF(sx-12,y+4),QPointF(sx+12,y+4))
    p.setPen(QPen(color(theme.light, 245), 1.4))
    p.drawLine(QPointF(sx-8,y+4),QPointF(sx+8,y+4))

def draw_bevel_panel(p, r, theme, cut=12, phase=0.0, routing=True, selected=False):
    path = bevel_rect(r, cut)
    fill=QLinearGradient(r.topLeft(),r.bottomRight())
    fill.setColorAt(0,color(theme.panel,235))
    fill.setColorAt(.36,color(theme.bg,224))
    fill.setColorAt(1,color(theme.panel,244))
    p.fillPath(path, fill)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(color(theme.accent,110 if selected else 80),4.2))
    p.drawPath(path)
    p.setPen(QPen(color(theme.accent,230 if selected else 168),1.1))
    p.drawPath(path)
    inner=r.adjusted(4,4,-4,-4)
    p.setPen(QPen(color(theme.light,42),.75))
    p.drawPath(bevel_rect(inner,max(4,cut-2)))
    sheen=QLinearGradient(r.x(),r.y(),r.x()+r.width()*.65,r.y()+r.height()*.65)
    sheen.setColorAt(0,color(theme.light,28))
    sheen.setColorAt(.37,color(theme.light,5))
    sheen.setColorAt(.55,color(theme.light,0))
    sheen.setColorAt(1,color(theme.light,0))
    p.save()
    p.setClipPath(path)
    p.fillRect(r,sheen)
    if routing:
        circuit_border(p,r,theme,0.9,phase)
    p.restore()

def draw_glyph(p, kind, rect, ink):
    """Icon-first monoline glyphs drawn at any DPI, independent of system fonts."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(rect.x(),rect.y())
    p.scale(rect.width()/24.0,rect.height()/24.0)
    p.setPen(QPen(color(ink),1.8,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    def line(*pts):
        for a,b in zip(pts[:-1],pts[1:]):
            p.drawLine(QPointF(*a),QPointF(*b))
    if kind in ("terminal","console"):
        p.drawRoundedRect(QRectF(2,4,20,16),2,2)
        line((6,9),(10,12),(6,15))
        line((12,16),(18,16))
    elif kind in ("folder","files"):
        line((2,8),(2,20),(22,20),(22,7),(11,7),(9,4),(2,4),(2,8))
    elif kind in ("home","dashboard"):
        line((2,11),(12,3),(22,11));line((5,10),(5,21),(19,21),(19,10))
        p.drawRect(QRectF(10,14,4,7))
    elif kind in ("apps","grid"):
        for x in (3,13):
            for y in (3,13):
                p.drawRoundedRect(QRectF(x,y,8,8),1,1)
    elif kind in ("settings","gear"):
        p.drawEllipse(QRectF(5,5,14,14));p.drawEllipse(QRectF(10,10,4,4))
        for a in range(0,360,45):
            t=math.radians(a)
            line((12+8*math.cos(t),12+8*math.sin(t)),(12+11*math.cos(t),12+11*math.sin(t)))
    elif kind in ("network","web"):
        p.drawEllipse(QRectF(3,3,18,18))
        p.drawEllipse(QRectF(8,3,8,18))
        line((3,12),(21,12))
    elif kind in ("layers","services"):
        for y in (5,10,15):
            line((3,y),(12,y+5),(21,y),(12,y+5),(3,y))
    elif kind in ("chip","cpu"):
        p.drawRect(QRectF(6,6,12,12))
        for v in (8,12,16):
            line((v,3),(v,6));line((v,18),(v,21))
            line((3,v),(6,v));line((18,v),(21,v))
    elif kind in ("storage","database"):
        p.drawEllipse(QRectF(4,3,16,6))
        line((4,6),(4,18));line((20,6),(20,18))
        p.drawArc(QRectF(4,15,16,6),180*16,180*16)
        line((4,11),(20,11))
    elif kind in ("monitor","activity"):
        p.drawRoundedRect(QRectF(2,4,20,16),2,2)
        line((4,13),(8,13),(10,8),(13,17),(16,11),(20,11))
    elif kind in ("shield","security"):
        path=QPainterPath();path.moveTo(12,2);path.lineTo(21,6);path.lineTo(19,15)
        path.quadTo(17,20,12,22);path.quadTo(7,20,5,15);path.lineTo(3,6);path.closeSubpath()
        p.drawPath(path);line((9,12),(11,14),(16,9))
    elif kind in ("search",):
        p.drawEllipse(QRectF(3,3,13,13));line((15,15),(22,22))
    elif kind in ("notification","bell"):
        p.drawArc(QRectF(5,5,14,14),0,180*16)
        line((5,12),(5,18),(19,18),(19,12));line((10,21),(14,21))
    elif kind in ("close",):
        line((5,5),(19,19));line((19,5),(5,19))
    elif kind in ("maximize",):
        p.drawRect(QRectF(4,4,16,16))
    elif kind in ("minimize",):
        line((4,17),(20,17))
    elif kind in ("save",):
        p.drawRoundedRect(QRectF(3,3,18,18),2,2)
        p.drawRect(QRectF(7,3,10,7));p.drawRect(QRectF(7,14,10,7))
    elif kind in ("plus",):
        line((12,3),(12,21));line((3,12),(21,12))
    elif kind in ("align",):
        for y in (5,12,19):line((3,y),(21,y))
    elif kind in ("cascade",):
        p.drawRect(QRectF(4,8,14,13));p.drawRect(QRectF(8,4,13,13))
    elif kind in ("power",):
        p.drawArc(QRectF(3,4,18,18),135*16,270*16);line((12,2),(12,12))
    elif kind in ("refresh",):
        p.drawArc(QRectF(4,4,16,16),40*16,270*16);line((18,4),(20,10),(14,9))
    elif kind in ("plug","extensions"):
        p.drawRoundedRect(QRectF(7,7,10,10),2,2)
        line((10,2),(10,7));line((14,2),(14,7));line((10,17),(10,22));line((14,17),(14,22))
    elif kind in ("logs",):
        p.drawRoundedRect(QRectF(5,3,14,18),1,1)
        for y in (8,12,16):line((8,y),(16,y))
    else:
        p.drawRoundedRect(QRectF(5,5,14,14),3,3)
        p.drawEllipse(QRectF(10,10,4,4))
    p.restore()

def icon(kind, theme, size=24):
    pix=QPixmap(size,size)
    pix.fill(Qt.GlobalColor.transparent)
    p=QPainter(pix)
    draw_glyph(p,kind,QRectF(.5,.5,size-1,size-1),theme.light)
    p.end()
    return QIcon(pix)

class NeonSurface(QFrame):
    """Reusable frame with procedural nine-slice-like geometry and glass effects."""
    def __init__(self, theme, parent=None, *, cut=11, routing=True, animated=False):
        super().__init__(parent)
        self.theme=theme
        self.cut=cut
        self.routing=routing
        self.phase=0.0
        self.setObjectName("neonSurface")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self._timer=None
        if animated:
            self._timer=QTimer(self)
            self._timer.setInterval(64)
            self._timer.timeout.connect(self._step)
            self._timer.start()
    def _step(self):
        if self.isVisible():
            self.phase=(self.phase+0.008)%1
            self.update()
    def apply_theme(self, theme):
        self.theme=theme
        self.update()
    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_bevel_panel(p,QRectF(self.rect()).adjusted(2,2,-2,-2),
                         self.theme,self.cut,self.phase,self.routing)
        p.end()
        super().paintEvent(event)

class NeonButton(QPushButton):
    """Real accessible Qt button with high-DPI neon geometry and icon."""
    def __init__(self, label="", glyph=None, theme=None, parent=None, *, compact=False):
        super().__init__(label,parent)
        self.theme=theme or THEMES["ElectroBlueNEON"]
        self.glyph=glyph
        self.hover=False
        self.compact=compact
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(30 if compact else 36)
        if compact: self.setMinimumWidth(32)
    def apply_theme(self, theme):
        self.theme=theme
        self.update()
    def enterEvent(self,e):
        self.hover=True;self.update();super().enterEvent(e)
    def leaveEvent(self,e):
        self.hover=False;self.update();super().leaveEvent(e)
    def paintEvent(self,e):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r=QRectF(self.rect()).adjusted(2,2,-2,-2)
        path=bevel_rect(r,7)
        grad=QLinearGradient(r.topLeft(),r.bottomLeft())
        grad.setColorAt(0,color(self.theme.accent,70 if self.hover else 36))
        grad.setColorAt(1,color(self.theme.panel,235))
        p.fillPath(path,grad)
        p.setPen(QPen(color(self.theme.light,240 if self.hover else 120),1.2))
        p.drawPath(path)
        if self.hover:
            p.setPen(QPen(color(self.theme.accent,90),3))
            p.drawLine(QPointF(r.x()+12,r.y()+2),QPointF(r.right()-12,r.y()+2))
        if self.glyph:
            ir=QRectF(r.x()+8, r.center().y()-9,18,18)
            if not self.text():ir=QRectF(r.center().x()-10,r.center().y()-10,20,20)
            draw_glyph(p,self.glyph,ir,self.theme.light)
        if self.text():
            p.setPen(color("#DFF5FF"))
            f=self.font();f.setPixelSize(12);f.setWeight(QFont.Weight.DemiBold)
            p.setFont(f)
            left=30 if self.glyph else 9
            p.drawText(r.adjusted(left,0,-7,0),Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       p.fontMetrics().elidedText(self.text(),Qt.TextElideMode.ElideRight,
                                                 max(30,int(r.width()-left-10))))
        p.end()

class NovaMark(QWidget):
    def __init__(self,theme,parent=None):
        super().__init__(parent)
        self.theme=theme
        self.setFixedSize(48,48)
    def apply_theme(self,theme):
        self.theme=theme;self.update()
    def paintEvent(self,e):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pts=QPolygonF([QPointF(24,2),QPointF(43,13),QPointF(43,35),
                       QPointF(24,46),QPointF(5,35),QPointF(5,13)])
        for width,alpha in ((7,35),(3,100),(1.6,255)):
            p.setPen(QPen(color(self.theme.accent,alpha),width));p.setBrush(Qt.BrushStyle.NoBrush);p.drawPolygon(pts)
        p.setPen(color(self.theme.light))
        font=QFont("DejaVu Sans",23,QFont.Weight.Bold)
        p.setFont(font);p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,"N")
        p.end()

def form_stylesheet(theme):
    a,b=theme.accent,theme.border
    return f"""
    QWidget {{color:#D5ECFF;font-family:'DejaVu Sans','Noto Sans',sans-serif; font-size:12px;}}
    QWidget#root {{background:{theme.bg};}}
    QLabel#muted {{color:#86A5BD;}}
    QLabel#brand {{font-size:19px;font-weight:700;color:#EBF9FF;}}
    QLabel#section {{font-size:11px;font-weight:700;color:{a};}}
    QLineEdit,QPlainTextEdit,QTextEdit,QTreeWidget,QComboBox,QListWidget {{
        background:#061626;color:#DCF5FF;border:1px solid {b};
        border-radius:5px;padding:5px;selection-background-color:#136E9B;}}
    QPlainTextEdit:focus,QLineEdit:focus {{border:1px solid {a};}}
    QMenu {{background:#071C2E;color:#DDF4FF;border:1px solid {a};padding:5px;}}
    QMenu::item {{padding:7px 28px;}}
    QMenu::item:selected {{background:#16577A;}}
    QSplitter::handle {{background:#115273;width:4px;}}
    QScrollBar:vertical {{background:#051423;width:9px;}}
    QScrollBar::handle:vertical {{background:#197DA5;border-radius:3px;}}
    QToolTip {{background:#0B2740;color:white;border:1px solid {a};padding:5px;}}
    QProgressBar {{border:1px solid {b};background:#071527;border-radius:4px;text-align:center;}}
    QProgressBar::chunk {{background:{a};border-radius:3px;}}
    QCheckBox::indicator {{width:14px;height:14px;}}
    """
