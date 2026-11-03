"""NOVA CONTROL CENTER native NEXUS HD control dialogs.

Settings and Sessions belong to the HOST shell, never to a terminal app.
SSH/API profiles are metadata only; secrets are not stored in JSON.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSettings, QUrl, QProcess
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QLinearGradient
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QComboBox, QLineEdit, QCheckBox, QSpinBox, QSlider,
    QListWidget, QListWidgetItem, QFileDialog, QDialogButtonBox, QMessageBox,
    QInputDialog
)
from .nexus_theme import PALETTES
from .nexus_v2_paint import vector_icon

PROFILE_DIR = Path.home()/".config"/"nova-control-center"
PROFILE_PATH = PROFILE_DIR/"connections-v1.json"
IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 _.-]{0,63}$")
SSH_HOST = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,252}$")
SSH_USER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$")

def load_profiles():
    try:
        obj=json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        if isinstance(obj,dict):
            return {"ssh":[r for r in obj.get("ssh",[]) if isinstance(r,dict)][:100],
                    "api":[r for r in obj.get("api",[]) if isinstance(r,dict)][:100]}
    except (OSError,ValueError,TypeError):
        pass
    return {"ssh":[],"api":[]}

def save_profiles(data):
    PROFILE_DIR.mkdir(mode=0o700,parents=True,exist_ok=True)
    os.chmod(PROFILE_DIR,0o700)
    temp=PROFILE_PATH.with_suffix(".tmp")
    # File always contains endpoints, usernames and *paths*, never credentials.
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    os.chmod(temp,0o600)
    temp.replace(PROFILE_PATH)

def validated_ssh(profile):
    host=str(profile.get("host","")).strip()
    user=str(profile.get("user","")).strip()
    port=int(profile.get("port",22))
    key=str(profile.get("identity","")).strip()
    if not SSH_HOST.fullmatch(host) or not SSH_USER.fullmatch(user) or not 1<=port<=65535:
        raise ValueError("Hôte, utilisateur ou port SSH invalide.")
    if not key:
        raise ValueError("Sélectionne une clé SSH.")
    path=Path(key).expanduser().resolve()
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError("Clé inexistante ou permissions trop ouvertes (chmod 600).")
    return ["ssh","-o","IdentitiesOnly=yes","-o","BatchMode=yes",
            "-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=8",
            "-i",str(path),"-p",str(port),"--",f"{user}@{host}","true"]

class NovaDialog(QDialog):
    """Resizable, frameless translucent Qt popup with crisp vector PCB traces."""
    def __init__(self,title,palette,parent=None):
        super().__init__(parent)
        self.palette=palette
        self._moving=None
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Dialog|Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(510,340)
        self.resize(650,530)
        main=QVBoxLayout(self)
        main.setContentsMargins(23,22,23,22)
        main.setSpacing(12)
        head=QHBoxLayout()
        self.icon=QLabel()
        self.icon.setPixmap(vector_icon("settings",palette.bright,28).pixmap(28,28))
        head.addWidget(self.icon)
        self.heading=QLabel(title)
        self.heading.setObjectName("popupHeading")
        head.addWidget(self.heading,1)
        close=QPushButton("×")
        close.setObjectName("popupClose")
        close.setFixedSize(30,30)
        close.clicked.connect(self.reject)
        head.addWidget(close)
        main.addLayout(head)
        self.content=QVBoxLayout()
        main.addLayout(self.content,1)
        self.setStyleSheet("""
        QDialog {background:transparent;}
        QLabel {color:#DAF2FF;font-size:12px;}
        QLabel#popupHeading {font-size:18px;font-weight:bold;color:#FFFFFF;}
        QPushButton {background:rgba(9,48,70,224);border:1px solid #217BA1;
            border-radius:4px;padding:7px;color:#DDF8FF;}
        QPushButton:hover {border-color:#75ECFF;background:rgba(17,82,109,234);}
        QLineEdit,QComboBox,QSpinBox,QListWidget {color:#E4F8FF;
            background:rgba(6,23,41,229);border:1px solid #29617E;
            border-radius:3px;padding:6px;}
        QTabWidget::pane {background:rgba(6,22,39,125);border:1px solid #245F7B;}
        QTabBar::tab {background:#103047;color:#DAF3FF;padding:10px 16px;}
        QTabBar::tab:selected {background:#155474;border-bottom:2px solid #47DFFF;}
        QCheckBox {color:#CDE9F8;}
        """)
    def set_palette(self,p):
        self.palette=p
        self.icon.setPixmap(vector_icon("settings",p.bright,28).pixmap(28,28))
        self.update()
    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r=self.rect().adjusted(7,7,-7,-7)
        x,y,w,h=r.x(),r.y(),r.width(),r.height()
        path=QPainterPath()
        path.moveTo(x+16,y)
        for xx,yy in ((x+w-16,y),(x+w,y+16),(x+w,y+h-16),
                      (x+w-16,y+h),(x+16,y+h),(x,y+h-16),(x,y+16)):
            path.lineTo(xx,yy)
        path.closeSubpath()
        opacity=max(55,min(95,int(QSettings("NOVA","ControlCenter").value("glass_opacity",82))))
        grad=QLinearGradient(x,y,x+w,y+h)
        grad.setColorAt(0,QColor(12,47,68,int(opacity*255/100)))
        grad.setColorAt(.65,QColor(4,17,33,int(opacity*255/100)))
        grad.setColorAt(1,QColor(13,39,59,int(opacity*255/100)))
        p.fillPath(path,grad)
        for thick,alpha in ((8,20),(4,40),(1.3,220)):
            c=QColor(self.palette.accent)
            c.setAlpha(alpha)
            p.setPen(QPen(c,thick))
            p.drawPath(path)
        p.setPen(QPen(QColor(self.palette.bright),1))
        # Three 45-degree traces are relative to the panel size.
        for i in range(3):
            ax=x+w*.53+i*11
            yy=y+9+i*7
            p.drawLine(int(ax),int(yy),int(ax+36),int(yy))
            p.drawLine(int(ax+36),int(yy),int(ax+47),int(yy+11))
            p.drawLine(int(ax+47),int(yy+11),int(ax+86),int(yy+11))
        # Fine red side traces with gentle pulse; don't alter the blue main frame.
        pulse=65+int(55*__import__("math").sin(__import__("time").monotonic()*1.3)**2)
        red=QColor("#FF4056")
        red.setAlpha(pulse)
        p.setPen(QPen(red,1.35))
        if h>90:
            p.drawLine(x+3,y+45,x+3,y+min(h-35,115))
            p.drawLine(x+w-3,y+h-115,x+w-3,y+h-45)
        p.end()
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and event.position().y()<63:
            handle=self.windowHandle()
            if handle and handle.startSystemMove():
                event.accept()
                return
            self._moving=event.globalPosition().toPoint()-self.pos()
            event.accept()
        else:super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        if self._moving is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint()-self._moving)
            event.accept()
        else:super().mouseMoveEvent(event)
    def mouseReleaseEvent(self,event):
        self._moving=None
        super().mouseReleaseEvent(event)

class ControlSettingsDialog(NovaDialog):
    applied=Signal(dict)
    def __init__(self,palette,parent=None):
        super().__init__("NOVA / PARAMÈTRES",palette,parent)
        settings=QSettings("NOVA","ControlCenter")
        form=QFormLayout()
        self.opacity=QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(55,95)
        self.opacity.setValue(int(settings.value("glass_opacity",82)))
        form.addRow("Transparence / opacité",self.opacity)
        self.animation=QCheckBox("Animations néon")
        self.animation.setChecked(str(settings.value("animations","true")).lower()=="true")
        form.addRow("Effets",self.animation)
        self.sidebar=QSpinBox()
        self.sidebar.setRange(160,420)
        self.sidebar.setSuffix(" px")
        self.sidebar.setValue(int(settings.value("sidebar_width",223)))
        form.addRow("Largeur barre latérale",self.sidebar)
        self.theme=QComboBox()
        self.theme.addItems(list(PALETTES))
        self.theme.setCurrentText(next((k for k,v in PALETTES.items() if v==palette),"ElectroBlueNEON"))
        form.addRow("Thème",self.theme)
        self.restore=QCheckBox("Restaurer le bureau au démarrage")
        self.restore.setChecked(str(settings.value("restore_workspace","true")).lower()=="true")
        form.addRow("Bureau",self.restore)
        self.content.addLayout(form)
        self.content.addWidget(QLabel(
            "Rendu adaptatif Qt : proportions des assets conservées, panneaux redimensionnables."))
        self.content.addStretch()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                  QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        self.content.addWidget(buttons)
    def save(self):
        data={"glass_opacity":self.opacity.value(),"animations":self.animation.isChecked(),
              "sidebar_width":self.sidebar.value(),"theme":self.theme.currentText(),
              "restore_workspace":self.restore.isChecked()}
        s=QSettings("NOVA","ControlCenter")
        for k,v in data.items():s.setValue(k,v)
        s.sync()
        self.applied.emit(data)
        self.accept()

class ControlSessionsDialog(NovaDialog):
    ssh_verified=Signal(str,bool)
    def __init__(self,palette,parent=None):
        super().__init__("NOVA / SESSIONS & CONNEXIONS",palette,parent)
        self.setMinimumSize(680,510)
        self.resize(760,590)
        self.data=load_profiles()
        self.process=None
        tabs=QTabWidget()
        self.content.addWidget(tabs)
        ssh=QWidget()
        layout=QVBoxLayout(ssh)
        self.ssh_list=QListWidget()
        self.ssh_list.currentItemChanged.connect(self.load_ssh)
        layout.addWidget(self.ssh_list)
        form=QFormLayout()
        self.name=QLineEdit()
        self.name.setPlaceholderText("GEN-1")
        self.host=QLineEdit()
        self.host.setPlaceholderText("server.example.org")
        self.user=QLineEdit()
        self.user.setPlaceholderText("sshuser")
        self.port=QSpinBox()
        self.port.setRange(1,65535)
        self.port.setValue(22)
        self.identity=QLineEdit()
        self.identity.setPlaceholderText("~/.ssh/id_ed25519")
        identity_row=QHBoxLayout()
        identity_row.addWidget(self.identity)
        pick=QPushButton("…")
        pick.clicked.connect(self.choose_key)
        identity_row.addWidget(pick)
        for label,field in (("Profil",self.name),("Hôte",self.host),
                            ("Utilisateur",self.user),("Port",self.port)):
            form.addRow(label,field)
        form.addRow("Clé SSH",identity_row)
        layout.addLayout(form)
        actions=QHBoxLayout()
        for name,fn in (("Enregistrer",self.store_ssh),
                        ("Générer clé Ed25519",self.generate_key),
                        ("Tester SSH",self.test_ssh)):
            b=QPushButton(name)
            b.clicked.connect(fn)
            actions.addWidget(b)
        layout.addLayout(actions)
        self.status=QLabel("Aucune connexion SSH active. Vérification d'hôte stricte.")
        layout.addWidget(self.status)
        tabs.addTab(ssh,"SSH / CLÉS")
        api=QWidget()
        apil=QVBoxLayout(api)
        self.api_list=QListWidget()
        self.api_list.currentItemChanged.connect(self.load_api)
        apil.addWidget(self.api_list)
        api_form=QFormLayout()
        self.api_name=QLineEdit()
        self.api_url=QLineEdit()
        self.api_url.setPlaceholderText("https://example.org/healthz")
        self.api_token=QLineEdit()
        self.api_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_token.setPlaceholderText("Jeton optionnel, jamais stocké dans JSON")
        api_form.addRow("Nom",self.api_name)
        api_form.addRow("URL",self.api_url)
        api_form.addRow("Token Bearer",self.api_token)
        apil.addLayout(api_form)
        api_actions=QHBoxLayout()
        btn=QPushButton("Enregistrer API")
        btn.clicked.connect(self.store_api)
        api_actions.addWidget(btn)
        test=QPushButton("Tester HTTPS")
        test.clicked.connect(self.test_api)
        api_actions.addWidget(test)
        apil.addLayout(api_actions)
        self.api_status=QLabel("HTTPS uniquement. Les tokens ne sont jamais journalisés.")
        self.api_status.setWordWrap(True)
        apil.addWidget(self.api_status)
        tabs.addTab(api,"API / APPS")
        self.network=QNetworkAccessManager(self)
        self.reply=None
        self.refresh()
    def refresh(self):
        self.ssh_list.clear()
        for entry in self.data["ssh"]:
            item=QListWidgetItem(entry.get("name",entry.get("host","SSH")))
            item.setData(Qt.ItemDataRole.UserRole,entry)
            self.ssh_list.addItem(item)
        self.api_list.clear()
        for entry in self.data["api"]:
            item=QListWidgetItem(entry.get("name","API"))
            item.setData(Qt.ItemDataRole.UserRole,entry)
            self.api_list.addItem(item)
    def load_ssh(self,item,previous=None):
        if item is None:return
        d=item.data(Qt.ItemDataRole.UserRole)
        self.name.setText(str(d.get("name","")))
        self.host.setText(str(d.get("host","")))
        self.user.setText(str(d.get("user","")))
        self.port.setValue(int(d.get("port",22)))
        self.identity.setText(str(d.get("identity","")))
    def load_api(self,item,previous=None):
        if item is None:return
        d=item.data(Qt.ItemDataRole.UserRole)
        self.api_name.setText(str(d.get("name","")))
        self.api_url.setText(str(d.get("url","")))
        self.api_token.clear()
    def choose_key(self):
        name,_=QFileDialog.getOpenFileName(self,"Sélectionner clé privée",str(Path.home()/".ssh"))
        if name:self.identity.setText(name)
    def ssh_profile(self):
        d={"name":self.name.text().strip(),"host":self.host.text().strip(),
           "user":self.user.text().strip(),"port":self.port.value(),
           "identity":self.identity.text().strip()}
        if not IDENTIFIER.fullmatch(d["name"]):
            raise ValueError("Nom de profil invalide.")
        validated_ssh(d)
        return d
    def store_ssh(self):
        try:
            d=self.ssh_profile()
            self.data["ssh"]=[r for r in self.data["ssh"] if r.get("name")!=d["name"]]+[d]
            save_profiles(self.data)
        except (ValueError,OSError) as exc:
            QMessageBox.warning(self,"SSH",str(exc))
            return
        self.refresh()
        self.status.setText("✓ Profil SSH sauvegardé")
    def generate_key(self):
        if not shutil.which("ssh-keygen"):
            QMessageBox.warning(self,"SSH","ssh-keygen introuvable.")
            return
        identifier=self.name.text().strip()
        if not IDENTIFIER.fullmatch(identifier):
            QMessageBox.warning(self,"SSH","Renseigne un nom de profil valide.")
            return
        name=re.sub(r"[^a-zA-Z0-9_-]","_",identifier)
        directory=Path.home()/".ssh"
        directory.mkdir(mode=0o700,parents=True,exist_ok=True)
        key=directory/("nova_"+name+"_ed25519")
        if key.exists() or Path(str(key)+".pub").exists():
            QMessageBox.warning(self,"SSH","Cette clé existe déjà ; aucun écrasement.")
            return
        QMessageBox.information(self,"Sécurité SSH",
            "Une phrase secrète est recommandée.\\n"
            "La commande ssh-keygen sera ouverte dans le terminal système.")
        # The interactive terminal handles the passphrase, rather than putting
        # it in argv where other processes might observe it.
        from PySide6.QtGui import QDesktopServices
        command="ssh-keygen -t ed25519 -a 64 -f "+__import__("shlex").quote(str(key))
        clipboard=__import__("PySide6.QtWidgets",fromlist=["QApplication"]).QApplication.clipboard()
        clipboard.setText(command)
        self.status.setText("Commande de génération copiée ; exécute-la dans un terminal.")
    def test_ssh(self):
        if self.process is not None:return
        try:
            d=self.ssh_profile()
            command=validated_ssh(d)
        except (ValueError,OSError) as exc:
            QMessageBox.warning(self,"SSH",str(exc))
            return
        self.process=QProcess(self)
        self.process.setProgram(command[0])
        self.process.setArguments(command[1:])
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.finished.connect(lambda code,status:self.finish_ssh(d["name"],code))
        self.process.errorOccurred.connect(lambda error:self.status.setText("✕ Erreur SSH : "+self.process.errorString()))
        self.process.start()
        self.status.setText("Vérification SSH en cours…")
    def finish_ssh(self,name,code):
        self.status.setText(("✓" if code==0 else "✕")+f" {name} — code {code}")
        self.ssh_verified.emit(name,code==0)
        self.process.deleteLater()
        self.process=None
    def api_profile(self):
        name=self.api_name.text().strip()
        url=QUrl(self.api_url.text().strip())
        if not IDENTIFIER.fullmatch(name) or not url.isValid() or url.scheme()!="https" or not url.host():
            raise ValueError("Profil et URL HTTPS valides obligatoires.")
        if url.userName() or url.password() or url.hasQuery() or url.hasFragment():
            raise ValueError("Ne place pas de secrets dans l'URL.")
        return {"name":name,"url":url.toString()}
    def store_api(self):
        try:
            d=self.api_profile()
            self.data["api"]=[r for r in self.data["api"] if r.get("name")!=d["name"]]+[d]
            save_profiles(self.data)
        except (ValueError,OSError) as exc:
            QMessageBox.warning(self,"API",str(exc))
            return
        token=self.api_token.text()
        self.api_status.setText("✓ Profil enregistré (sans token).")
        if token:
            try:
                import keyring
                keyring.set_password("NOVA-Control-Center/API",d["name"],token)
                self.api_status.setText("✓ Profil enregistré et token protégé par le trousseau.")
            except Exception:
                self.api_status.setText("✓ Profil enregistré. Token NON sauvegardé : trousseau indisponible.")
        self.refresh()
    def test_api(self):
        if self.reply is not None:return
        try:
            d=self.api_profile()
        except ValueError as exc:
            QMessageBox.warning(self,"API",str(exc))
            return
        request=QNetworkRequest(QUrl(d["url"]))
        request.setTransferTimeout(10000)
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        token=self.api_token.text()
        if not token:
            try:
                import keyring
                token=keyring.get_password("NOVA-Control-Center/API",d["name"]) or ""
            except Exception:
                token=""
        if token:
            request.setRawHeader(b"Authorization",b"Bearer "+token.encode("utf-8"))
        self.api_status.setText("◌ Connexion HTTPS…")
        self.reply=self.network.get(request)
        self.reply.finished.connect(self.api_finished)
    def api_finished(self):
        reply=self.reply
        self.reply=None
        if reply is None:return
        status=reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if reply.error():
            self.api_status.setText("✕ "+reply.errorString())
        else:
            self.api_status.setText(f"✓ Réponse HTTP {status}")
        reply.deleteLater()
    def closeEvent(self,event):
        if self.process is not None:
            self.process.kill()
            self.process.waitForFinished(300)
        if self.reply is not None:self.reply.abort()
        super().closeEvent(event)
