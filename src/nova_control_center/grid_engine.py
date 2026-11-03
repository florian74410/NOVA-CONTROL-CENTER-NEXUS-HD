"""Qt Graphics View based 9x9 snap grid, rendered exclusively by the HUB."""
from __future__ import annotations
from PySide6.QtCore import Qt,QRectF,QPointF,Signal
from PySide6.QtGui import QColor,QPen,QBrush,QPainter
from PySide6.QtWidgets import QGraphicsView,QGraphicsScene,QGraphicsObject,QGraphicsSimpleTextItem

CELLS=9
SIZES={"small":(1,1),"medium":(2,3),"large":(3,3)}
class Tile(QGraphicsObject):
    def __init__(self,grid,key,title,x,y,w,h):
        super().__init__()
        self.grid=grid;self.key=key;self.title=title
        self.xcell=x;self.ycell=y;self.wcell=w;self.hcell=h
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable,True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges,True)
        self.setZValue(2)
        self.setPos(x*grid.unit,y*grid.unit)
        self.caption=QGraphicsSimpleTextItem(title,self)
        self.caption.setBrush(QColor("#a8eaff"))
        self.caption.setPos(9,7)
    def boundingRect(self): return QRectF(0,0,self.wcell*self.grid.unit,self.hcell*self.grid.unit)
    def paint(self,painter,option,widget=None):
        painter.setPen(QPen(QColor("#27c9ee"),1.5))
        painter.setBrush(QBrush(QColor(12,27,44,235)))
        painter.drawRoundedRect(self.boundingRect().adjusted(2,2,-2,-2),5,5)
    def mouseReleaseEvent(self,event):
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
    def add_tile(self,title,w=2,h=3):
        spots=self.positions(w,h)
        if not spots:return None
        self.serial+=1;key=str(self.serial);x,y=spots[0]
        tile=Tile(self,key,title,x,y,w,h)
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
