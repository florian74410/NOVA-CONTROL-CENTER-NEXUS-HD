"""Original NEXUS effects: single Qt animation clock and themed toast surfaces.

No unlicensed stock GIFs. Animations are native Qt and can be exported as GIF.
"""
from __future__ import annotations
from PySide6.QtCore import Qt, QTimer, QPoint, QRectF, Signal, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QPen, QColor, QLinearGradient, QFont, QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QGraphicsOpacityEffect
from .nexus_v2_paint import draw_frame, qcolor, vector_icon

class PulseIndicator(QLabel):
    """Native QLabel paint path: avoids PySide6 Python QWidget.paintEvent crashes.

    Animation changes a tiny off-screen QPixmap; QLabel handles final paint in
    C++ (important for PySide6/Shiboken versions observed on Mint XFCE).
    """
    def __init__(self,palette,parent=None):
        super().__init__(parent)
        self.palette=palette
        self.phase=0.0
        self.setFixedSize(28,28)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground,True)
        self.timer=QTimer(self)
        self.timer.setInterval(90)
        self.timer.timeout.connect(self.tick)
        self._render()
        self.timer.start()

    def tick(self):
        if self.isVisible():
            self.phase=(self.phase+.045)%1
            self._render()

    def set_palette(self,p):
        self.palette=p
        self._render()

    def _render(self):
        pm=QPixmap(28,28)
        pm.fill(Qt.GlobalColor.transparent)
        painter=QPainter(pm)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(qcolor(self.palette.accent,42))
            painter.setPen(QPen(qcolor(self.palette.accent,75),1))
            radius=8+self.phase*5
            painter.drawEllipse(pm.rect().center(),int(radius),int(radius))
            painter.setBrush(qcolor("#26E6AC"))
            painter.setPen(QPen(qcolor("#B8FFE7"),1))
            painter.drawEllipse(pm.rect().center(),4,4)
            # Tiny red detail: symmetric circuit endpoints.
            painter.setPen(QPen(QColor("#FF485D"),1.3))
            painter.drawLine(1,12,1,17)
            painter.drawLine(26,12,26,17)
        finally:
            painter.end()
        self.setPixmap(pm)

class Toast(QWidget):
    dismissed=Signal(object)
    TYPES={
        "success":("#26E7A9","check"),
        "error":("#FF4862","close"),
        "warning":("#FFBE44","bell"),
        "info":("#35CFFF","bell"),
    }
    def __init__(self,palette,message,kind="info",parent=None):
        super().__init__(parent)
        self.palette=palette
        self.kind=kind if kind in self.TYPES else "info"
        self.setFixedSize(360,76)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("nexusToast")
        lay=QHBoxLayout(self)
        lay.setContentsMargins(17,14,13,14)
        color,icon=self.TYPES[self.kind]
        image=QLabel()
        image.setPixmap(vector_icon(icon,color,27).pixmap(25,25))
        lay.addWidget(image)
        label=QLabel(message)
        label.setWordWrap(True)
        label.setMaximumWidth(255)
        lay.addWidget(label,1)
        dismiss=QPushButton()
        dismiss.setIcon(vector_icon("close","#DBF3FF",18))
        dismiss.setFixedSize(24,24)
        dismiss.clicked.connect(self.finish)
        lay.addWidget(dismiss)
        self.fade=QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.fade)
        self.anim=QVariantAnimation(self)
        self.anim.setDuration(260)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.valueChanged.connect(self.fade.setOpacity)
        self.anim.start()
        self.delay=QTimer(self)
        self.delay.setSingleShot(True)
        self.delay.timeout.connect(self.finish)
        self.delay.start(3400)
    def finish(self):
        if getattr(self,"_finishing",False):return
        self._finishing=True
        self.delay.stop()
        self.anim.stop()
        self.anim.setStartValue(float(self.fade.opacity()))
        self.anim.setEndValue(0.0)
        self.anim.setDuration(220)
        try:self.anim.finished.disconnect()
        except (RuntimeError,TypeError):pass
        self.anim.finished.connect(lambda:self.dismissed.emit(self))
        self.anim.start()
    def set_palette(self,p):
        self.palette=p
        self.update()
    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_frame(p,QRectF(self.rect()).adjusted(5,5,-5,-5),self.palette)
        color=self.TYPES[self.kind][0]
        p.setPen(QPen(QColor(color),2.5))
        p.drawLine(19,self.height()-7,self.width()-22,self.height()-7)
        p.end()

class NotificationLayer(QWidget):
    def __init__(self,host,palette):
        super().__init__(host)
        self.host=host
        self.palette=palette
        self.toasts=[]
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground,True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground,True)
        self.hide()
    def add(self,text,kind="info"):
        toast=Toast(self.palette,text,kind,self)
        toast.dismissed.connect(self.remove)
        self.toasts.append(toast)
        self.setGeometry(self.host.rect())
        self.raise_()
        self.show()
        toast.show()
        self.rearrange()
    def remove(self,toast):
        if toast in self.toasts:self.toasts.remove(toast)
        toast.deleteLater()
        self.rearrange()
        if not self.toasts:self.hide()
    def rearrange(self):
        self.setGeometry(self.host.rect())
        for idx,toast in enumerate(reversed(self.toasts[-4:])):
            toast.move(max(5,self.width()-toast.width()-23),
                       max(5,self.height()-toast.height()-24-idx*84))
    def resizeEvent(self,event):
        self.rearrange()
        super().resizeEvent(event)
    def set_palette(self,p):
        self.palette=p
        for toast in self.toasts:toast.set_palette(p)
