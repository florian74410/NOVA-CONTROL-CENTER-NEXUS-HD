"""Qt Graphics View based 9x9 snap grid, rendered exclusively by the HUB."""
from __future__ import annotations
from PySide6.QtCore import Qt,QRectF,QPointF,Signal
from PySide6.QtGui import QColor,QPen,QBrush,QPainter
from PySide6.QtWidgets import QGraphicsView,QGraphicsScene,QGraphicsObject,QGraphicsSimpleTextItem

CELLS=9
SIZES={"small":(1,2),"medium":(2,3),"large":(4,4)}
class Tile(QGraphicsObject):
    def __init__(self,grid,key,title,x,y,w,h):
        super().__init__()
        self.grid=grid;self.key=key;self.title=title
        self.xcell=x;self.ycell=y;self.wcell=w;self.hcell=h
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable,True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges,True)
        self.setZValue(2)
        self._action=None
        self._size_start=None
        self._size_cells=None
        self.setAcceptHoverEvents(True)
        self.setPos(x*grid.unit,y*grid.unit)
        self.caption=QGraphicsSimpleTextItem(title,self)
        self.caption.setBrush(QColor("#a8eaff"))
        self.caption.setPos(9,7)
    def boundingRect(self): return QRectF(0,0,self.wcell*self.grid.unit,self.hcell*self.grid.unit)
    def paint(self,painter,option,widget=None):
        painter.setPen(QPen(QColor("#27c9ee"),1.5))
        painter.setBrush(QBrush(QColor(12,27,44,235)))
        rect=self.boundingRect().adjusted(3,3,-3,-3)
        painter.drawRoundedRect(rect,6,6)
        # Slim opposing red PCB accents and visible close/resize affordances.
        painter.setPen(QPen(QColor("#FF4864"),1.4))
        painter.drawLine(rect.left()+1,rect.top()+25,rect.left()+1,min(rect.top()+65,rect.bottom()-10))
        painter.drawLine(rect.right()-1,max(rect.top()+10,rect.bottom()-65),rect.right()-1,rect.bottom()-25)
        painter.setPen(QPen(QColor("#FF7892"),1.5))
        painter.drawLine(rect.right()-18,rect.top()+9,rect.right()-9,rect.top()+18)
        painter.drawLine(rect.right()-9,rect.top()+9,rect.right()-18,rect.top()+18)
        painter.drawLine(rect.right()-18,rect.bottom()-9,rect.right()-9,rect.bottom()-18)
        painter.drawLine(rect.right()-11,rect.bottom()-9,rect.right()-9,rect.bottom()-11)
    def mousePressEvent(self,event):
        rect=self.boundingRect()
        point=event.pos()
        # Controls must remain inside the cells, not on the grid node.
        if point.x() >= rect.width()-25 and point.y()<=25:
            self.grid.remove_tile(self.key)
            event.accept()
            return
        if point.x()>=rect.width()-26 and point.y()>=rect.height()-26:
            self._action="resize"
            self._size_start=event.scenePos()
            self._size_cells=(self.wcell,self.hcell)
            event.accept()
            return
        super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        if self._action=="resize":
            # Dynamic preview is avoided until release; snapping never overlaps.
            event.accept()
            return
        super().mouseMoveEvent(event)
    def hoverMoveEvent(self,event):
        rect=self.boundingRect()
        point=event.pos()
        if point.x()>=rect.width()-26 and point.y()>=rect.height()-26:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif point.x()>=rect.width()-25 and point.y()<=25:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().hoverMoveEvent(event)
    def mouseReleaseEvent(self,event):
        if self._action=="resize":
            start=self._size_start
            oldw,oldh=self._size_cells
            self._action=None
            self._size_start=None
            self._size_cells=None
            dx=round((event.scenePos().x()-start.x())/self.grid.unit)
            dy=round((event.scenePos().y()-start.y())/self.grid.unit)
            self.resize_cells(max(1,min(CELLS-self.xcell,oldw+dx)),
                              max(1,min(CELLS-self.ycell,oldh+dy)))
            event.accept()
            return
        if self.scene() is None:
            event.accept()
            return

        super().mouseReleaseEvent(event)
        u=self.grid.unit
        x=max(0,min(CELLS-self.wcell,round(self.pos().x()/u)))
        y=max(0,min(CELLS-self.hcell,round(self.pos().y()/u)))
        if not self.grid.can_place(x,y,self.wcell,self.hcell,ignore=self.key):
            x,y=self.xcell,self.ycell
        self.xcell,self.ycell=x,y
        self.setPos(x*u,y*u)
        self.grid.changed.emit()
    def resize_cells(self,w,h):
        if not (w>=2 or h>=2):return False
        if not self.grid.can_place(self.xcell,self.ycell,w,h,ignore=self.key):return False
        self.prepareGeometryChange();self.wcell=w;self.hcell=h;self.update()
        self.grid.changed.emit();return True

class GridScene(QGraphicsScene):
    changed=Signal()
    def __init__(self,parent=None):
        super().__init__(parent)
        self.unit=50;self.tiles={};self.serial=0
        self.setSceneRect(0,0,450,450)
        self.setBackgroundBrush(QColor("#08111d"))
    def drawBackground(self,painter,rect):
        super().drawBackground(painter,rect)
        painter.setPen(QPen(QColor("#526478"),0.7,Qt.PenStyle.DotLine))
        for i in range(CELLS+1):
            p=i*self.unit
            painter.drawLine(QPointF(p,0),QPointF(p,CELLS*self.unit))
            painter.drawLine(QPointF(0,p),QPointF(CELLS*self.unit,p))
    def can_place(self,x,y,w,h,ignore=None):
        if min(x,y)<0 or w<1 or h<1 or x+w>CELLS or y+h>CELLS:return False
        for key,t in self.tiles.items():
            if key!=ignore and x<t.xcell+t.wcell and x+w>t.xcell and y<t.ycell+t.hcell and y+h>t.ycell:
                return False
        return True
    def positions(self,w,h):
        return [(x,y) for y in range(CELLS-h+1) for x in range(CELLS-w+1) if self.can_place(x,y,w,h)]
    def add_tile(self,title,w=2,h=3,tile_class=Tile):
        if w<1 or h<1 or (w==1 and h==1):return None
        spots=self.positions(w,h)
        if not spots:return None
        self.serial+=1;key=str(self.serial);x,y=spots[0]
        tile=tile_class(self,key,title,x,y,w,h)
        self.tiles[key]=tile;self.addItem(tile);self.changed.emit()
        return tile
    def remove_tile(self,key):
        tile=self.tiles.pop(key,None)
        if tile:self.removeItem(tile);self.changed.emit()
    def resize_grid(self,side):
        side=max(12,int(side))
        if side==self.unit:return
        self.unit=side
        self.setSceneRect(0,0,side*CELLS,side*CELLS)
        for tile in self.tiles.values():
            tile.prepareGeometryChange()
            tile.setPos(tile.xcell*side,tile.ycell*side)
            tile.update()
        self.update()
    def layout(self):
        return [{"id":t.key,"title":t.title,"x":t.xcell,"y":t.ycell,"w":t.wcell,"h":t.hcell} for t in self.tiles.values()]

class GridView(QGraphicsView):
    def __init__(self,parent=None):
        self.grid=GridScene()
        super().__init__(self.grid,parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("QGraphicsView{border:0;background:#08111d}")
        self.resize_grid()
    def resize_grid(self):
        size=max(12,min(max(0,self.viewport().width()-10),max(0,self.viewport().height()-10))//CELLS)
        self.grid.resize_grid(size)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.resize_grid()
