"""N3XV5 universal lightweight 2D widget engine.

Single Qt Graphics View scene: no browser, embedded peripheral GUI or animation timer.
A 9x9 grid holds 1x2 / 2x1 / 3x3 / 9x9 reusable frames. CLI data is
represented as priority-tagged display items; Qt owns every pixel.
"""
from __future__ import annotations

from dataclasses import dataclass
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QColor, QPen, QBrush, QPainter, QFont, QPainterPath
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsObject, QMenu

CELLS = 9
SIZES = {"small_v": (1, 2), "small_h": (2, 1), "medium": (3, 3), "large": (9, 9)}
BLUE = QColor("#19bfff")
DIM = QColor("#3a6a82")
TEXT = QColor("#d6f3ff")
BG = QColor("#091521")


@dataclass(frozen=True)
class DisplayItem:
    label: str
    value: str
    priority: int = 1


def visible_items(items, width, height):
    """P1 on every frame, P2 on medium/large, P3 only on large.

    Items are stable-sorted by priority; density is bounded by tile area.
    """
    level = 3 if (width, height) == SIZES["large"] else 2 if width >= 3 and height >= 3 else 1
    capacity = 48 if level == 3 else 8 if level == 2 else 1
    return sorted((i for i in items if 1 <= i.priority <= level),
                  key=lambda i: i.priority)[:capacity]


class Tile(QGraphicsObject):
    def __init__(self, grid, key, title, x, y, w, h, items=None):
        super().__init__()
        self.grid, self.key, self.title = grid, key, title
        self.xcell, self.ycell, self.wcell, self.hcell = x, y, w, h
        self.data = list(items or [])
        self.setFlags(self.GraphicsItemFlag.ItemIsMovable |
                      self.GraphicsItemFlag.ItemIsSelectable |
                      self.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)
        self.setZValue(2)
        self.setPos(x * grid.unit, y * grid.unit)

    def boundingRect(self):
        return QRectF(0, 0, self.wcell * self.grid.unit, self.hcell * self.grid.unit)

    def set_data(self, items):
        self.data = list(items)
        self.update()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.boundingRect().adjusted(1.5, 1.5, -1.5, -1.5)
        painter.setPen(QPen(BLUE if self.isSelected() else DIM, 1.4))
        painter.setBrush(QBrush(BG))
        painter.drawRoundedRect(r, 4, 4)
        # PCB routing: thin orthogonal tracks with tiny circular vias.
        painter.setPen(QPen(QColor("#175374"), 0.8))
        x1, y1 = r.left()+7, r.bottom()-7
        painter.drawLine(QPointF(x1, y1), QPointF(x1+10, y1))
        painter.drawLine(QPointF(x1+10, y1), QPointF(x1+10, y1-6))
        painter.drawEllipse(QPointF(x1+10, y1-6), 1.7, 1.7)
        painter.setPen(QPen(BLUE, 2))
        corner = min(11, r.width()/5, r.height()/5)
        for x, sx in ((r.left(), 1), (r.right(), -1)):
            for y, sy in ((r.top(), 1), (r.bottom(), -1)):
                painter.drawLine(QPointF(x, y+sy*corner), QPointF(x, y))
                painter.drawLine(QPointF(x, y), QPointF(x+sx*corner, y))
        painter.setClipRect(r.adjusted(6, 5, -6, -5))
        font = QFont("DejaVu Sans", 9, QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(TEXT)
        heading = self.title if self.wcell >= 3 else self.title.split("/")[-1].strip()
        painter.drawText(QRectF(7, 3, r.width()-14, 17),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, heading)
        painter.setPen(QPen(QColor("#246b8d"), 0.7))
        painter.drawLine(QPointF(8, 22), QPointF(max(8,r.width()-8), 22))
        data = visible_items(self.data, self.wcell, self.hcell)
        painter.setFont(QFont("DejaVu Sans", 8))
        painter.setPen(TEXT)
        available = max(0, r.height()-25)
        step = max(11, min(24, available/max(1,len(data))))
        for index, item in enumerate(data):
            if 24+index*step+step > r.height(): break
            label = item.value if self.wcell < 3 else f"{item.label}: {item.value}"
            painter.drawText(QRectF(8, 24+index*step, max(1,r.width()-16), step),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        u = self.grid.unit
        x = max(0, min(CELLS-self.wcell, round(self.pos().x()/u)))
        y = max(0, min(CELLS-self.hcell, round(self.pos().y()/u)))
        if not self.grid.can_place(x, y, self.wcell, self.hcell, ignore=self.key):
            x, y = self.xcell, self.ycell
        self.xcell, self.ycell = x, y
        self.setPos(x*u, y*u)
        self.grid.changed.emit()

    def contextMenuEvent(self, event):
        menu = QMenu()
        for name, (w, h) in SIZES.items():
            action = menu.addAction(f"Format {name} ({w}x{h})")
            action.setEnabled(self.grid.can_place(self.xcell, self.ycell, w, h, ignore=self.key))
            action.triggered.connect(lambda checked=False, w=w, h=h: self.resize_cells(w, h))
        menu.addSeparator()
        menu.addAction("Supprimer l'iFrame", lambda: self.grid.remove_tile(self.key))
        menu.exec(event.screenPos())
        event.accept()

    def resize_cells(self, w, h):
        if (w, h) not in SIZES.values(): return False
        if not self.grid.can_place(self.xcell, self.ycell, w, h, ignore=self.key):
            return False
        self.prepareGeometryChange()
        self.wcell, self.hcell = w, h
        self.update()
        self.grid.changed.emit()
        return True


class GridScene(QGraphicsScene):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.unit = 50
        self.tiles = {}
        self.serial = 0
        self.setSceneRect(0, 0, 450, 450)
        self.setBackgroundBrush(QBrush(QColor("#060e18")))

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        painter.setPen(QPen(QColor("#26465c"), 0.7, Qt.PenStyle.DotLine))
        for i in range(CELLS+1):
            p = i*self.unit
            painter.drawLine(QPointF(p, 0), QPointF(p, CELLS*self.unit))
            painter.drawLine(QPointF(0, p), QPointF(CELLS*self.unit, p))

    def can_place(self, x, y, w, h, ignore=None):
        if min(x,y) < 0 or w < 1 or h < 1 or x+w > CELLS or y+h > CELLS:
            return False
        for key, t in self.tiles.items():
            if key != ignore and x < t.xcell+t.wcell and x+w > t.xcell and y < t.ycell+t.hcell and y+h > t.ycell:
                return False
        return True

    def positions(self, w, h):
        return [(x,y) for y in range(CELLS-h+1) for x in range(CELLS-w+1)
                if self.can_place(x,y,w,h)]

    def add_tile(self, title, w=3, h=3, items=None):
        if (w,h) not in SIZES.values(): return None
        spots = self.positions(w,h)
        if not spots: return None
        self.serial += 1
        key = str(self.serial)
        x,y = spots[0]
        tile = Tile(self,key,title,x,y,w,h,items)
        self.tiles[key] = tile
        self.addItem(tile)
        self.changed.emit()
        return tile

    def remove_tile(self, key):
        tile = self.tiles.pop(str(key),None)
        if tile is not None:
            self.removeItem(tile)
            self.changed.emit()

    def resize_grid(self, side):
        side = max(12,int(side))
        if side == self.unit: return
        # prepareGeometryChange must precede unit mutation.
        for tile in self.tiles.values(): tile.prepareGeometryChange()
        self.unit = side
        self.setSceneRect(0,0,side*CELLS,side*CELLS)
        for tile in self.tiles.values():
            tile.setPos(tile.xcell*side,tile.ycell*side)
            tile.update()
        self.update()

    def layout(self):
        return [{"id":t.key,"title":t.title,"x":t.xcell,"y":t.ycell,
                 "w":t.wcell,"h":t.hcell} for t in self.tiles.values()]


class GridView(QGraphicsView):
    def __init__(self,parent=None):
        self.grid = GridScene()
        super().__init__(self.grid,parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("QGraphicsView{border:0;background:#060e18}")
        self.resize_grid()

    def resize_grid(self):
        size = max(12,min(max(0,self.viewport().width()-10),
                          max(0,self.viewport().height()-10))//CELLS)
        self.grid.resize_grid(size)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.resize_grid()
