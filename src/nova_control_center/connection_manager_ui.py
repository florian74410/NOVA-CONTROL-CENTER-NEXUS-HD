"""NOVA Core 'Créer une connexion' : dedicated forms for seven protocols."""
from __future__ import annotations
import uuid
from pathlib import Path
from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import (
 QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QStackedWidget,QComboBox,
 QListWidget,QListWidgetItem,QLineEdit,QPushButton,QLabel,QCheckBox,
 QSpinBox,QMessageBox,QSplitter
)
from .control_panels import NovaDialog
from .connection_registry import PROTOCOLS,DEFAULT_PORT,ConnectionDefinition,normalize,readiness

class ProtocolForm(QWidget):
    def __init__(self,protocol,parent=None):
        super().__init__(parent)
        self.protocol=protocol
        self.fields={}
        outer=QVBoxLayout(self)
        details={
            "FTP":"FTP/FTPS : FTPS privilégié. Aucun mot de passe enregistré dans ce formulaire.",
            "SSH":"SSH : chemin de clé privée du compte Linux. Authentification distante à la demande.",
            "HTTPS":"HTTPS : URL et méthode de test ; tokens gérés séparément par le trousseau.",
            "MYSQL":"MySQL : connexion distante avec TLS.",
            "SQLITE":"SQLite : chemin de base locale, lecture seule par défaut.",
            "SMTP":"SMTP : connexion SSL ou STARTTLS.",
            "TCP":"TCP : connexion de socket, sans authentification ni échange applicatif.",
        }
        note=QLabel(details[protocol])
        note.setWordWrap(True)
        outer.addWidget(note)
        form=QFormLayout()
        outer.addLayout(form)
        def text(name,title,default=""):
            widget=QLineEdit(default)
            self.fields[name]=widget
            form.addRow(title,widget)
        def number(name,title,default):
            widget=QSpinBox()
            widget.setRange(1,65535)
            widget.setValue(default)
            self.fields[name]=widget
            form.addRow(title,widget)
        def choices(name,title,items):
            widget=QComboBox()
            widget.addItems(items)
            self.fields[name]=widget
            form.addRow(title,widget)
        if protocol=="SQLITE":
            text("path","Fichier SQLite",str(Path.home()/"data.sqlite3"))
            widget=QCheckBox("Lecture seule")
            widget.setChecked(True)
            self.fields["readonly"]=widget
            form.addRow("Mode",widget)
        elif protocol=="HTTPS":
            text("url","Adresse","https://example.org/health")
            choices("method","Méthode",["HEAD","GET"])
        else:
            text("host","Serveur","localhost")
            number("port","Port",DEFAULT_PORT[protocol] or 8080)
        if protocol in ("FTP","SSH","MYSQL","SMTP"):
            text("username","Utilisateur")
        if protocol=="SSH":text("identity","Clé privée",str(Path.home()/".ssh/id_ed25519"))
        if protocol=="FTP":
            choices("mode","Sécurité",["FTPS","FTP"])
            text("remote_dir","Dossier distant","/")
        if protocol=="MYSQL":
            text("database","Base")
            choices("tls","TLS",["required","verify_identity"])
        if protocol=="SMTP":choices("tls","TLS",["SSL","STARTTLS"])
        time=QSpinBox()
        time.setRange(2,20)
        time.setValue(7)
        time.setSuffix(" s")
        self.fields["timeout"]=time
        form.addRow("Timeout",time)
        outer.addStretch()
    def read(self):
        result={}
        for key,widget in self.fields.items():
            if isinstance(widget,QSpinBox):result[key]=widget.value()
            elif isinstance(widget,QCheckBox):result[key]=widget.isChecked()
            elif isinstance(widget,QComboBox):result[key]=widget.currentText()
            else:result[key]=widget.text().strip()
        return result
    def fill(self,options):
        for key,value in options.items():
            widget=self.fields.get(key)
            if isinstance(widget,QSpinBox):widget.setValue(int(value))
            elif isinstance(widget,QCheckBox):widget.setChecked(bool(value))
            elif isinstance(widget,QComboBox):widget.setCurrentText(str(value))
            elif isinstance(widget,QLineEdit):widget.setText(str(value))

class ConnectionManagerDialog(NovaDialog):
    saved=Signal(str)
    activated=Signal(str)
    def __init__(self,palette,cache,parent=None):
        super().__init__("NOVA / CONNEXIONS DE LA SESSION",palette,parent)
        self.resize(940,640)
        self.setMinimumSize(760,520)
        self.cache=cache
        self.registry=cache.registry
        self.edit_id=None
        user=self.registry.identity
        self.content.addWidget(QLabel(
            f"Session : {user.username} / UID {user.uid}"+
            (" / administrateur local" if user.administrator else " / utilisateur local")))
        splitter=QSplitter(Qt.Orientation.Horizontal)
        self.content.addWidget(splitter,1)
        left=QWidget()
        l=QVBoxLayout(left)
        l.addWidget(QLabel("MES CONNEXIONS PRÉCHARGÉES"))
        self.saved_list=QListWidget()
        self.saved_list.itemSelectionChanged.connect(self.load_selected)
        l.addWidget(self.saved_list,1)
        add=QPushButton("＋ Créer une connexion")
        add.clicked.connect(self.reset)
        l.addWidget(add)
        refresh=QPushButton("↻ Actualiser le registre")
        refresh.clicked.connect(self.refresh)
        l.addWidget(refresh)
        splitter.addWidget(left)
        right=QWidget()
        v=QVBoxLayout(right)
        v.addWidget(QLabel("PARAMÉTRAGE PAR PROTOCOLE"))
        row=QHBoxLayout()
        self.name=QLineEdit()
        self.name.setPlaceholderText("Nom du profil")
        row.addWidget(self.name,2)
        self.protocol=QComboBox()
        self.protocol.addItems(PROTOCOLS)
        self.protocol.currentIndexChanged.connect(self.switch)
        row.addWidget(self.protocol,1)
        v.addLayout(row)
        self.pages={}
        self.stack=QStackedWidget()
        for p in PROTOCOLS:
            page=ProtocolForm(p)
            self.pages[p]=page
            self.stack.addWidget(page)
        v.addWidget(self.stack,1)
        actions=QHBoxLayout()
        for label,handler in (("Enregistrer",self.save_profile),
                              ("Sélectionner",self.activate),
                              ("Supprimer",self.delete_profile)):
            button=QPushButton(label)
            button.clicked.connect(handler)
            actions.addWidget(button)
        v.addLayout(actions)
        self.message=QLabel("Les clés sont recherchées uniquement dans le contexte de ton compte.")
        self.message.setWordWrap(True)
        v.addWidget(self.message)
        splitter.addWidget(right)
        splitter.setSizes([275,640])
        self.refresh()
    def switch(self,index):
        self.stack.setCurrentIndex(index)
    def refresh(self):
        self.cache.preload()
        self.saved_list.blockSignals(True)
        self.saved_list.clear()
        for item in self.cache.list():
            p=item.profile
            label=f"{p.protocol} · {p.name}  [{item.state}]"
            row=QListWidgetItem(label)
            row.setData(Qt.ItemDataRole.UserRole,p.connection_id)
            self.saved_list.addItem(row)
        self.saved_list.blockSignals(False)
    def reset(self):
        self.saved_list.clearSelection()
        self.edit_id=None
        self.name.clear()
        self.protocol.setCurrentIndex(0)
        self.message.setText("Sélectionne un protocole pour configurer une nouvelle connexion.")
    def load_selected(self):
        selected=self.saved_list.selectedItems()
        if not selected:return
        connection_id=selected[0].data(Qt.ItemDataRole.UserRole)
        try:record=self.cache.get(connection_id)
        except (KeyError,PermissionError,RuntimeError):return
        self.edit_id=connection_id
        self.name.setText(record.profile.name)
        self.protocol.setCurrentText(record.profile.protocol)
        self.pages[record.profile.protocol].fill(record.profile.options)
        self.message.setText(f"État : {record.state}. Aucune connexion réseau établie automatiquement.")
    def current(self):
        return normalize(ConnectionDefinition(self.edit_id or uuid.uuid4().hex,
            self.name.text().strip(),self.protocol.currentText(),
            self.pages[self.protocol.currentText()].read()))
    def save_profile(self):
        try:
            item=self.registry.upsert(self.current())
            self.edit_id=item.connection_id
            self.refresh()
            self.saved.emit(item.connection_id)
            self.message.setText("✓ Profil enregistré et préchargé pour cette session.")
        except (ValueError,OSError,TypeError) as exc:
            QMessageBox.warning(self,"Connexion",str(exc))
    def activate(self):
        try:
            profile=self.current()
            stored=self.cache.get(profile.connection_id)
            if stored.state in ("MISSING_KEY","KEY_PERMISSIONS","MISSING_FILE"):
                self.message.setText("Connexion indisponible : clé ou fichier manquant.")
                return
            self.activated.emit(profile.connection_id)
            self.message.setText(f"✓ {profile.name} sélectionnée ; authentification réseau à la demande.")
        except (ValueError,OSError,KeyError,PermissionError,RuntimeError) as exc:
            self.message.setText("Enregistre d'abord ce profil : "+str(exc))
    def delete_profile(self):
        if not self.edit_id:return
        if QMessageBox.question(self,"Supprimer",
                 "Supprimer ce profil de connexion ?")==QMessageBox.StandardButton.Yes:
            self.registry.remove(self.edit_id)
            self.edit_id=None
            self.refresh()
