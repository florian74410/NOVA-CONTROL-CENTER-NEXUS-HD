"""NEXUS V2 scalable vector rendering: PCB routes, clipped glass, glow, icons."""
from __future__ import annotations
import math
from functools import lru_cache
from PySide6.QtCore import Qt, QPointF, QRectF, QSize, QTimer
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QPen, QBrush, QLinearGradient,
    QRadialGradient, QPixmap, QIcon, QFont
)
from PySide6.QtWidgets import QWidget, QPushButton, QFrame
from PySide6.QtSvg import QSvgRenderer
from .nexus_theme import PALETTES

ICONS = {
    "apps": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    "terminal": '<rect x="2.5" y="4" width="19" height="16" rx="2"/><path d="m6 9 4 3-4 3 M12 16h6"/>',
    "folder": '<path d="M2 7V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2z"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c-6 5-6 13 0 18M12 3c6 5 6 13 0 18"/>',
    "monitor": '<rect x="2" y="3" width="20" height="16" rx="2"/><path d="M5 12h3l2-4 3 8 2-5h4M8 22h8"/>',
    "boxes": '<path d="m12 2 9 5-9 5-9-5zM3 7v10l9 5 9-5V7M12 12v10"/>',
    "network": '<circle cx="12" cy="4" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><path d="M11 6 6 17M13 6l5 11M7 19h10"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M10 2h4l1 3 3 1 3-1 2 4-2 2v3l2 2-2 4-3-1-3 1-1 3h-4l-1-3-3-1-3 1-2-4 2-2v-3L1 9l2-4 3 1 3-1z"/>',
    "shield": '<path d="m12 2 9 4v6c0 5-3 8-9 10-6-2-9-5-9-10V6z"/><path d="m8 12 3 3 5-6"/>',
    "layers": '<path d="m12 2 10 5-10 5L2 7zM2 12l10 5 10-5M2 17l10 5 10-5"/>',
    "search": '<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6"/>',
    "bell": '<path d="M6 17h12l-2-3V9a4 4 0 0 0-8 0v5zM10 21h4"/>',
    "home": '<path d="m3 11 9-8 9 8M5 10v11h14V10M10 21v-7h4v7"/>',
    "save": '<path d="M4 3h14l3 4v14H3V3zM7 3v7h10V3M7 21v-8h10v8"/>',
    "grid": '<rect x="2" y="2" width="9" height="9"/><rect x="13" y="2" width="9" height="9"/><rect x="2" y="13" width="9" height="9"/><rect x="13" y="13" width="9" height="9"/>',
    "list": '<path d="M8 5h14M8 12h14M8 19h14"/><circle cx="3" cy="5" r="1"/><circle cx="3" cy="12" r="1"/><circle cx="3" cy="19" r="1"/>',
    "close": '<path d="M5 5 19 19M19 5 5 19"/>',
    "maximize": '<rect x="4" y="4" width="16" height="16" rx="1"/>',
    "minimize": '<path d="M4 17h16"/>',
    "plus": '<path d="M12 3v18M3 12h18"/>',
    "chevron": '<path d="m8 4 8 8-8 8"/>',
    "refresh": '<path d="M20 6v6h-6M4 18v-6h6M5 10A8 8 0 0 1 19 7M19 14a8 8 0 0 1-14 3"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 4 18 4 18 0V5M3 12c0 4 18 4 18 0"/>',
}
def qcolor(value, alpha=255):
    c = QColor(value)
    c.setAlpha(alpha)
    return c

@lru_cache(maxsize=256)
def vector_icon(name: str, accent: str = "#59DBFF", size: int = 24) -> QIcon:
    path = ICONS.get(name, ICONS["apps"])
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
           'fill="none" stroke="' + accent + '" stroke-width="1.65" '
           'stroke-linecap="round" stroke-linejoin="round">' + path + '</svg>')
    renderer = QSvgRenderer(svg.encode("utf-8"))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return QIcon(pm)

def chamfer(rect: QRectF, cut=13):
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    c = min(cut, w/4, h/4)
    path = QPainterPath()
    path.moveTo(x+c, y)
    path.lineTo(x+w-c, y)
    path.lineTo(x+w, y+c)
    path.lineTo(x+w, y+h-c)
    path.lineTo(x+w-c, y+h)
    path.lineTo(x+c, y+h)
    path.lineTo(x, y+h-c)
    path.lineTo(x, y+c)
    path.closeSubpath()
    return path

def draw_frame(p: QPainter, rect: QRectF, palette, strength=1.0, animated=0.0):
    """Glass fill + inset outlines + routed corners. No fixed-size bitmaps."""
    if rect.width() < 24 or rect.height() < 24:
        return
    path = chamfer(rect, 13)
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0, qcolor("#133954", 234))
    grad.setColorAt(.13, qcolor("#0A2034", 228))
    grad.setColorAt(.63, qcolor("#061323", 227))
    grad.setColorAt(1, qcolor("#102A41", 238))
    p.fillPath(path, QBrush(grad))
    p.setBrush(Qt.BrushStyle.NoBrush)
    for width, alpha in ((8, int(17*strength)), (4, int(42*strength)), (1.25, int(205*strength))):
        p.setPen(QPen(qcolor(palette.accent, min(255, alpha)), width))
        p.drawPath(path)
    inset = rect.adjusted(5, 5, -5, -5)
    p.setPen(QPen(qcolor(palette.bright, 67), .7))
    p.drawPath(chamfer(inset, 11))
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    # Conductive tracks: continuous right-angle/45-degree routes, no triangles.
    p.setPen(QPen(qcolor(palette.accent, 110), 1.0))
    for i in range(3):
        yy = y + 8 + i*5
        route = QPainterPath(QPointF(x+w*.53, yy))
        route.lineTo(x+w*.64, yy)
        route.lineTo(x+w*.64+9, yy+9)
        route.lineTo(x+w*.78, yy+9)
        p.drawPath(route)
        p.drawEllipse(QRectF(x+w*.78-2, yy+7, 4, 4))
    p.setPen(QPen(qcolor(palette.bright, 190), 2.1))
    p.drawLine(QPointF(x+22, y+1), QPointF(x+min(w*.28, 150), y+1))
    shine = (math.sin(animated * math.tau)+1)/2
    if animated:
        xx = x + 20 + (w-40)*shine
        p.setPen(QPen(qcolor(palette.bright, 150), 2.5))
        p.drawLine(QPointF(xx-18, y+1), QPointF(xx+18, y+1))
    p.setPen(QPen(qcolor(palette.accent, 180), 1.5))
    for off in range(3):
        sx = x + w - 76 + off*11
        sy = y + h - 9
        p.drawLine(QPointF(sx, sy), QPointF(sx+9, sy-8))

class NexusPanel(QFrame):
    """Transparent child container inside a painted glass PCB frame."""
    def __init__(self, palette, parent=None, glow=False):
        super().__init__(parent)
        self.palette = palette
        self.glow = glow
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("nexusPanel")
    def set_palette(self, palette):
        self.palette = palette
        self.update()
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_frame(p, QRectF(self.rect()).adjusted(5,5,-5,-5), self.palette,
                   1.15 if self.glow else .75)
        p.end()

class NexusButton(QPushButton):
    def __init__(self, label="", icon_name=None, parent=None, primary=False):
        super().__init__(label, parent)
        self.icon_name = icon_name
        self.primary = primary
        self.palette = PALETTES["ElectroBlueNEON"]
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(33)
        if icon_name:
            self.setIcon(vector_icon(icon_name))
            self.setIconSize(QSize(17, 17))
    def set_palette(self, palette):
        self.palette = palette
        if self.icon_name:
            self.setIcon(vector_icon(self.icon_name, palette.bright, 20))
        self.update()
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(2,2,-2,-2)
        active = self.isDown() or self.isChecked()
        hover = self.underMouse()
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, qcolor(self.palette.accent, 110 if active else 67 if hover else 29))
        grad.setColorAt(1, qcolor("#071728", 245))
        outline = chamfer(rect, 7)
        p.fillPath(outline, grad)
        p.setPen(QPen(qcolor(self.palette.bright if active or hover else self.palette.accent,
                             225 if active or hover else 118), 1.15))
        p.drawPath(outline)
        p.end()
        # Let QPushButton paint icon and label, but suppress default button chrome.
        super().paintEvent(event)

class NexusBackdrop(QWidget):
    """Cached scenic-free abstract PCB canvas; no invented wallpaper dependencies."""
    def __init__(self, palette, parent=None):
        super().__init__(parent)
        self.palette = palette
        self.cache = None
    def set_palette(self, palette):
        self.palette = palette
        self.cache = None
        self.update()
    def resizeEvent(self, event):
        self.cache = None
        super().resizeEvent(event)
    def paintEvent(self, event):
        if self.cache is None or self.cache.size() != self.size():
            pm = QPixmap(self.size())
            pm.fill(qcolor(self.palette.background))
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            radial = QRadialGradient(w*.70, h*.38, max(1,w*.7))
            radial.setColorAt(0, qcolor(self.palette.accent, 38))
            radial.setColorAt(1, qcolor(self.palette.background, 0))
            p.fillRect(self.rect(), radial)
            for n in range(22):
                from_left = n % 2 == 0
                x = (n*47) % max(1, int(w*.39))
                y = (n*51) % max(1, h)
                if not from_left: x = w-x
                sign = 1 if from_left else -1
                p.setPen(QPen(qcolor(self.palette.accent, 24+(n%5)*11), 1.0))
                path = QPainterPath(QPointF(x,y))
                path.lineTo(x+sign*24,y)
                path.lineTo(x+sign*50,y+26)
                path.lineTo(x+sign*(95+n%4*15),y+26)
                p.drawPath(path)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qcolor(self.palette.bright, 80+(n%4)*15))
                p.drawEllipse(QPointF(x+sign*(95+n%4*15),y+26), 2.3, 2.3)
            p.end()
            self.cache = pm
        p = QPainter(self)
        p.drawPixmap(0,0,self.cache)
        p.end()
