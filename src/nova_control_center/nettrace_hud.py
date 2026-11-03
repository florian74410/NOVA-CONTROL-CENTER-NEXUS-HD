"""N3XV5 NetTrace adaptive 2D tile renderer.

The CLI provides redacted diagnostic data only. All Qt painting, layout,
placement, resizing and removal is exclusively controlled by HUB GridScene.
"""
from __future__ import annotations
import math
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPen
from .grid_engine import Tile, GridView
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QFileDialog

COMMANDS=("probe","dns","tcp","tls","har","correlate")
MAX_TEXT=180

def brief(value,limit=30):
    if value is None:return "—"
    s=str(value).replace("\n"," ").replace("\r"," ").strip()
    return s[:limit-1]+"…" if len(s)>limit else s

def compact_report(report,cells):
    """Pure data selection; cells is (w,h). No sensitive payloads allowed."""
    if not isinstance(report,dict):
        return {"tier":"small","headline":"NO DATA","rows":[],"severity":"warning"}
    w,h=cells
    area=w*h
    tier="large" if area>=12 and w>=3 and h>=3 else ("medium" if area>=5 else "small")
    command=brief(report.get("command","probe"),14).upper()
    data=report.get("data",{})
    if not isinstance(data,dict):data={}
    error=data.get("error")
    status=data.get("status")
    if command=="PROBE":
        headline=("ERR "+brief(error,12)) if error else ("HTTP "+brief(status,7) if status is not None else "HTTP —")
        base=[
            ("LAT",brief(data.get("duration_ms"),10)+" ms"),
            ("HOST",brief(data.get("target"),MAX_TEXT)),
            ("IP",brief(data.get("remote_ip"),40)),
            ("METHOD",brief(data.get("method"),10)),
        ]
        steps=data.get("timings_ms") or {}
        if isinstance(steps,dict):
            for key in ("namelookup_ms","connect_ms","appconnect_ms","starttransfer_ms","total_ms"):
                if key in steps:base.append((key.replace("_ms","").upper(),brief(steps[key],15)+" ms"))
        if isinstance(data.get("diagnosis"),dict):
            base.append(("CAUSE",brief(data["diagnosis"].get("issue"),MAX_TEXT)))
            base.append(("ACTION",brief(data["diagnosis"].get("advice"),MAX_TEXT)))
        if isinstance(data.get("response_headers"),dict):
            for key in ("content-type","server","x-request-id","cache-control"):
                if key in data["response_headers"]:
                    base.append((key.upper(),brief(data["response_headers"][key],MAX_TEXT)))
    elif command=="DNS":
        addresses=data.get("addresses",[])
        headline="DNS OK" if addresses else "DNS ERROR"
        base=[("HOST",data.get("host")),("LOOKUP",str(data.get("duration_ms","—"))+" ms")]
        base.extend(("ADDRESS",value) for value in addresses[:6])
    elif command=="TCP":
        headline="TCP OPEN" if data.get("open") else "TCP CLOSED"
        base=[("ENDPOINT",str(data.get("host",""))+":"+str(data.get("port",""))),
              ("CONNECT",str(data.get("duration_ms","—"))+" ms"),
              ("ERROR",data.get("error"))]
    elif command=="TLS":
        headline="TLS VALID" if data.get("valid") else "TLS ERROR"
        base=[("HOST",data.get("host")),("VERSION",data.get("tls_version")),
              ("CIPHER",data.get("cipher")),("CERT EXPIRES",data.get("not_after")),
              ("HANDSHAKE",str(data.get("handshake_ms","—"))+" ms")]
    elif command=="HAR":
        headline="HAR "+brief(data.get("entries"),8)+" REQS"
        base=[("ERRORS",data.get("errors")),("ENTRIES",data.get("entries"))]
        for item in (data.get("slowest") or [])[:8]:
            if isinstance(item,dict):
                base.append((str(item.get("status","?")),str(item.get("duration_ms","?"))+"ms "+brief(item.get("target"),64)))
    elif command=="CORRELATE":
        matches=data.get("server_matches") or []
        headline="VPS "+str(len(matches))+" MATCH"
        base=[("REQUEST",data.get("request_id")),
              ("CLIENT",str((data.get("client") or {}).get("status","?"))),
              ("LOG MATCHES",len(matches))]
        for item in matches[:10]:
            if isinstance(item,dict):
                base.append(("UPSTREAM",str(item.get("upstream_status","?"))+
                    " "+str(item.get("upstream_response_time","?"))+"s"))
    else:
        headline="NETTRACE"
        base=[]
    base=[(brief(label,20),brief(value,MAX_TEXT)) for label,value in base if value is not None]
    severe=bool(error) or (isinstance(status,int) and status>=400) or (
        command=="TLS" and not data.get("valid")) or (
        command=="TCP" and not data.get("open"))
    limit={"small":1,"medium":5,"large":24}[tier]
    return {"tier":tier,"headline":headline,"command":command,
            "rows":base[:limit],"severity":"error" if severe else "ok",
            "hidden":max(0,len(base)-limit)}

class NetTraceTile(Tile):
    def __init__(self,grid,key,title,x,y,w,h):
        super().__init__(grid,key,title,x,y,w,h)
        self.report={"command":"probe","data":{"status":None,"duration_ms":None}}
        self.caption.setVisible(False)

    def set_report(self,report):
        self.report=report
        self.update()

    def paint(self,painter,option,widget=None):
        super().paint(painter,option,widget)
        model=compact_report(self.report,(self.wcell,self.hcell))
        rect=self.boundingRect().adjusted(10,8,-10,-10)
        if rect.width()<40 or rect.height()<50:return
        painter.save()
        try:
            painter.setClipRect(rect)
            painter.setPen(QColor("#B6F3FF"))
            painter.setFont(QFont("DejaVu Sans",max(7,min(11,int(self.grid.unit*.13))),QFont.Weight.Bold))
            painter.drawText(QRectF(rect.left()+2,rect.top()+2,rect.width()-28,20),
                             Qt.AlignmentFlag.AlignLeft, "NETTRACE // "+model["command"])
            severity=QColor("#FF5269" if model["severity"]=="error" else "#37F5C3")
            painter.setPen(QPen(severity,1.6))
            painter.drawLine(rect.left(),rect.top()+26,rect.right()-3,rect.top()+26)
            painter.setFont(QFont("DejaVu Sans",max(8,min(15,int(self.grid.unit*.2))),QFont.Weight.Bold))
            painter.drawText(QRectF(rect.left()+2,rect.top()+29,rect.width()-4,27),
                             Qt.AlignmentFlag.AlignLeft,model["headline"])
            y=rect.top()+63
            max_lines=max(0,int((rect.height()-69)//18))
            rows=model["rows"][:max_lines]
            painter.setFont(QFont("DejaVu Sans",max(7,min(10,int(self.grid.unit*.12)))))
            for label,value in rows:
                painter.setPen(QColor("#73AFC8"))
                label_text=label+":"
                painter.drawText(QRectF(rect.left()+2,y,rect.width()*.38,17),
                                 Qt.AlignmentFlag.AlignLeft,label_text)
                painter.setPen(QColor("#E1F7FF"))
                painter.drawText(QRectF(rect.left()+rect.width()*.38,y,rect.width()*.60,17),
                                 Qt.AlignmentFlag.AlignLeft,brief(value,40))
                y+=18
            hidden=model["hidden"]+max(0,len(model["rows"])-len(rows))
            if hidden and rect.height()>=130:
                painter.setPen(QColor("#FF657A"))
                painter.drawText(QRectF(rect.left()+2,rect.bottom()-17,rect.width()-5,16),
                                 Qt.AlignmentFlag.AlignRight,
                                 "+"+str(hidden)+" détails · agrandir ↘")
        finally:
            painter.restore()

class NetTracePanel(QWidget):
    """2D page: only the HUB constructs widgets, CLI sends JSON diagnostics."""
    requested=Signal(str,str)
    def __init__(self,parent=None):
        super().__init__(parent)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(4,4,4,4)
        layout.setSpacing(5)
        bar=QHBoxLayout()
        bar.setSpacing(7)
        bar.addWidget(QLabel("NETTRACE //"))
        self.command=QComboBox(self)
        self.command.addItems(["probe","dns","tcp","tls","har","correlate"])
        self.command.setToolTip("Type de diagnostic à exécuter dans NetTrace CLI")
        bar.addWidget(self.command)
        self.target=QLineEdit(self)
        self.target.setPlaceholderText("https://vps.example.org/api/health")
        self.target.returnPressed.connect(self.run)
        bar.addWidget(self.target,1)
        start=QPushButton("▶ DIAGNOSTIC")
        start.clicked.connect(self.run)
        bar.addWidget(start)
        new=QPushButton("+ iFrame")
        new.clicked.connect(self.new_tile)
        bar.addWidget(new)
        layout.addLayout(bar)
        self.grid_view=GridView(self)
        layout.addWidget(self.grid_view,1)
        self.status=QLabel("CLI déconnecté · sélectionne un test pour afficher ses résultats")
        layout.addWidget(self.status)
        self.tile=None
        self.new_tile()
        self.command.currentTextChanged.connect(self._placeholder)

    def _placeholder(self,command):
        hints={"probe":"https://vps.example.org/api/health",
               "dns":"vps.example.org","tcp":"vps.example.org:443",
               "tls":"vps.example.org:443",
               "har":"Fichier HAR Firefox (sélection automatique)",
               "correlate":"Rapport client + logs VPS (sélection automatique)"}
        self.target.setPlaceholderText(hints.get(command,""))
        self.target.setEnabled(command not in ("har","correlate"))

    def new_tile(self):
        scene=self.grid_view.grid
        if self.tile is not None and self.tile.scene() is scene:
            self.tile.setSelected(True)
            return self.tile
        tile=scene.add_tile("NETTRACE",2,3,tile_class=NetTraceTile)
        self.tile=tile
        if tile is None:self.status.setText("Grille 9×9 pleine · libère 2×3 cellules")
        return tile

    def run(self):
        command=self.command.currentText()
        if command=="har":
            filename,_=QFileDialog.getOpenFileName(self,"Importer HAR Firefox","",
                                                     "HTTP Archive (*.har *.json)")
            if not filename:return
            target=filename
        elif command=="correlate":
            client,_=QFileDialog.getOpenFileName(self,"Rapport NetTrace client","",
                                                  "NetTrace JSON (*.json)")
            if not client:return
            server,_=QFileDialog.getOpenFileName(self,"Logs JSONL VPS","",
                                                  "Logs JSONL (*.jsonl *.log *.txt)")
            if not server:return
            target=__import__("json").dumps([client,server])
        else:
            target=self.target.text().strip()
        if not target:
            self.status.setText("Saisis une URL, un domaine ou une adresse hôte:port")
            return
        self.new_tile()
        self.status.setText("Diagnostic "+command+" en cours via IPC Unix…")
        self.requested.emit(command,target)

    def apply_report(self,payload):
        if not isinstance(payload,dict) or payload.get("command") not in COMMANDS:
            return False
        tile=self.new_tile()
        if tile is None:return False
        tile.set_report(payload)
        model=compact_report(payload,(tile.wcell,tile.hcell))
        self.status.setText("NETTRACE / "+model["headline"]+
                            " · double action: glisser, redimensionner ↘, supprimer ✕")
        return True
