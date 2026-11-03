"""NEXUS HD 0.8 inspired, resolution-independent Qt theme engine."""
from dataclasses import dataclass
import math
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QLinearGradient, QPainterPath
from PySide6.QtWidgets import QWidget

@dataclass(frozen=True)
class Palette:
    key: str
    accent: str
    bright: str
    background: str
    panel: str
    edge: str

PALETTES = {
    "ElectroBlueNEON": Palette("ElectroBlueNEON", "#00CFFF", "#76E9FF", "#07101E", "#10253A", "#266B91"),
    "RougeERROR": Palette("RougeERROR", "#FF294C", "#FF8495", "#110A10", "#2A111B", "#913249"),
}

def rgba(value, alpha=255):
    c = QColor(value)
    c.setAlpha(alpha)
    return c

def stylesheet(p: Palette):
    return """
    QWidget { color: #D9EDFC; font-family: 'DejaVu Sans', 'Noto Sans', sans-serif; font-size: 12px; }
    QMainWindow, QWidget#root, QFrame#outer { background: %s; }
    QWidget#topbar, QWidget#sidebar { background: %s; border: 1px solid %s; }
    QWidget#topbar { border-bottom: 2px solid %s; }
    QWidget#sidebar { border-radius: 7px; }
    QLabel#brand { color: %s; font-weight: bold; font-size: 17px; }
    QLabel#muted { color: #829DB1; }
    QLabel#section { color: %s; font-weight: bold; font-size: 11px; }
    QLabel#status { color: #A8CBE0; }
    QPushButton { color: #D8F5FF; background: %s; border: 1px solid %s; border-radius: 5px;
                  padding: 6px 10px; min-height: 20px; }
    QPushButton:hover { border: 1px solid %s; background: #1B435E; }
    QPushButton:pressed { background: #276584; }
    QPushButton#primary { background: %s; color: #05131E; font-weight: bold; }
    QPushButton#rail { background: transparent; border: 1px solid transparent;
                       min-height: 35px; padding: 8px; text-align: left; }
    QPushButton#rail:hover { background: #153C58; border-color: %s; }
    QPushButton#rail:checked { border-left: 3px solid %s; background: #16334A; }
    QLineEdit, QTextEdit, QPlainTextEdit, QTreeWidget, QListWidget, QComboBox {
        background: #071626; color: #CBEAFF; border: 1px solid %s; border-radius: 4px;
        selection-background-color: #16618A; padding: 5px;
    }
    QTextEdit:focus, QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid %s; }
    QMenu { background: %s; border: 1px solid %s; padding: 5px; }
    QMenu::item { padding: 8px 24px; }
    QMenu::item:selected { background: #1C4864; }
    QToolTip { color: white; background: #10273A; border: 1px solid %s; }
    QScrollBar:vertical { background: #071321; width: 9px; }
    QScrollBar::handle:vertical { background: #24617D; border-radius: 3px; }
    QSplitter::handle { background: #215270; width: 4px; }
    """ % (p.background, p.panel, p.edge, p.accent, p.bright,
           p.accent, p.panel, p.edge, p.bright, p.accent, p.edge, p.accent,
           p.edge, p.bright, p.panel, p.edge, p.accent)

class CircuitCanvas(QWidget):
    """Cheap static PCB painter. Render only when resized/theme changes."""
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("circuitCanvas")
        self.setAutoFillBackground(False)
        self._cached = None

    def set_theme(self, theme):
        self.theme = theme
        self._cached = None
        self.update()

    def resizeEvent(self, event):
        self._cached = None
        super().resizeEvent(event)

    def paintEvent(self, event):
        from PySide6.QtGui import QPixmap
        if self._cached is None or self._cached.size() != self.size():
            self._cached = QPixmap(self.size())
            self._cached.fill(rgba(self.theme.background))
            p = QPainter(self._cached)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            shade = QLinearGradient(0, 0, w, h)
            shade.setColorAt(0, rgba(self.theme.panel, 180))
            shade.setColorAt(0.48, rgba(self.theme.background))
            shade.setColorAt(1, rgba(self.theme.panel, 125))
            p.fillRect(self.rect(), shade)
            for i in range(8):
                x = int(w * 0.07 + i * 29)
                y = int(h * 0.04 + i * 20)
                pen = QPen(rgba(self.theme.accent, 45 + (i % 3) * 18), 1.25)
                p.setPen(pen)
                path = QPainterPath()
                path.moveTo(x, 0)
                path.lineTo(x, y)
                path.lineTo(x + 15, y + 15)
                path.lineTo(min(w, x + 135), y + 15)
                p.drawPath(path)
                p.drawEllipse(QRectF(min(w, x + 133), y + 13, 4, 4))
                yy = max(20, h - y)
                p.drawLine(max(0, w - x), h, max(0, w - x), yy)
                p.drawLine(max(0, w - x), yy, max(0, w - x - 110), yy)
            p.end()
        qp = QPainter(self)
        qp.drawPixmap(0, 0, self._cached)
