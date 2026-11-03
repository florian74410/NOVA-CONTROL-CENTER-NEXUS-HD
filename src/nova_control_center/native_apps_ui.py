"""N3XV5 native peripheral package and shared session manager dialog.

Local .deb imports are verified SHA256 and staged offline. Installation is a
separate, explicit polkit prompt; a .deb is NEVER executed during import.
"""
from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,
    QFileDialog,QMessageBox,QInputDialog
)
from .control_panels import NovaDialog
from .n3xv5_bridge import manifest_from_json

class NativeAppsDialog(NovaDialog):
    def __init__(self,palette,hub,parent=None):
        super().__init__("N3XV5 / APPLICATIONS PÉRIPHÉRIQUES",palette,parent)
        self.resize(760,540)
        self.hub=hub
        self.process=None
        self.pending_app=None
        self.content.addWidget(QLabel(
            "Packages natifs Linux .deb · Dépendances hors ligne · Permissions par application"))
        self.apps=QListWidget()
        self.content.addWidget(self.apps,1)
        self.status=QLabel("Importation locale puis installation système avec confirmation.")
        self.status.setWordWrap(True)
        self.content.addWidget(self.status)
        actions=QHBoxLayout()
        for caption,handler in (
            ("Importer .deb + manifeste",self.import_package),
            ("Installer sélection",self.install_selected),
            ("Lancer sélection",self.launch_selected),
            ("Actualiser",self.refresh)):
            btn=QPushButton(caption)
            btn.clicked.connect(handler)
            actions.addWidget(btn)
        self.content.addLayout(actions)
        self.refresh()

    def refresh(self):
        self.apps.clear()
        for app_id,record in sorted(self.hub.package_manager.list().items()):
            m=record["manifest"]
            self.apps.addItem(f'{app_id}  |  {m["version"]}  |  {record["state"]}')
            self.apps.item(self.apps.count()-1).setData(0x100,app_id)

    def selected(self):
        item=self.apps.currentItem()
        if item is None:
            QMessageBox.information(self,"Application","Sélectionne une application.")
            return None
        return item.data(0x100)

    def import_package(self):
        descriptor,_=QFileDialog.getOpenFileName(
            self,"Manifeste N3XV5","", "N3XV5 manifest (*.json)")
        if not descriptor:return
        try:
            data=Path(descriptor).read_bytes()
            if len(data)>65536:raise ValueError("Manifeste trop volumineux")
            manifest=manifest_from_json(data)
            if manifest.platform.value!="linux-x64":
                raise ValueError("Cette application ne cible pas Linux AMD64")
            if self.hub.session_manager.session.locked:
                raise PermissionError("Déverrouille le HUB avant toute installation")
            if manifest.dependencies:
                raise ValueError(
                    "Dépendances manquantes : importer les SHA-256 dans Dependancy "
                    "avant de référencer l'application. Le catalogue sécurisé "
                    "ne télécharge aucune bibliothèque.")
            package,_=QFileDialog.getOpenFileName(
                self,"Paquet natif Linux (.deb)","", "Debian package (*.deb)")
            if not package:return
            message=(f"Importer {manifest.name} {manifest.version} ?\n"
                     f"Paquet: {manifest.package_name}\n"
                     f"SHA256: {manifest.package_sha256}\n"
                     f"Permissions demandées: {', '.join(manifest.capabilities) or 'aucune'}\n"
                     "Aucun droit n'est accordé automatiquement.")
            if QMessageBox.question(self,"Vérification / Importation",message)!=QMessageBox.StandardButton.Yes:
                return
            target=self.hub.package_manager.stage(manifest,package)
            self.status.setText("Paquet vérifié et placé dans le cache : "+str(target))
            self.refresh()
        except (OSError,ValueError,PermissionError,TypeError,KeyError) as exc:
            QMessageBox.warning(self,"Importation refusée",str(exc))

    def install_selected(self):
        app_id=self.selected()
        if not app_id:return
        if self.hub.session_manager.session.locked:
            QMessageBox.warning(self,"Session verrouillée","Déverrouille la session HUB.")
            return
        if self.process is not None and self.process.state()!=QProcess.ProcessState.NotRunning:
            QMessageBox.warning(self,"Installation","Une installation est déjà en cours.")
            return
        if shutil.which("pkexec") is None or not Path("/usr/bin/apt-get").is_file():
            QMessageBox.warning(self,"Installation","pkexec ou apt-get indisponible.")
            return
        try:
            path=self.hub.package_manager.verified_staged_package(app_id)
            manifest=self.hub.package_manager.list()[app_id]["manifest"]
        except (OSError,ValueError,KeyError,PermissionError) as exc:
            QMessageBox.warning(self,"Vérification",str(exc))
            return
        if QMessageBox.question(self,"Installation système",
            "Installer ce paquet Linux vérifié sur l'ordinateur ?\n"
            +str(path)+"\nUn dialogue système demandera les droits nécessaires."
            )!=QMessageBox.StandardButton.Yes:return
        self.pending_app=app_id
        self.process=QProcess(self)
        self.process.finished.connect(self.on_install_finished)
        self.process.errorOccurred.connect(
            lambda error:self.status.setText("Erreur de lancement de l'installateur: "+str(error)))
        self.process.start("pkexec",["/usr/bin/apt-get","install","-y",str(path)])
        self.status.setText("Installation demandée pour "+app_id+" — confirmation système requise.")

    def on_install_finished(self,code,status):
        app_id=self.pending_app
        self.pending_app=None
        if not app_id:return
        if code!=0 or status!=QProcess.ExitStatus.NormalExit:
            self.status.setText("Installation non validée : code "+str(code))
            return
        self.hub.package_manager.mark_installed(app_id)
        declared=self.hub.package_manager.list()[app_id]["manifest"]["capabilities"]
        approved=[]
        for cap in declared:
            if QMessageBox.question(self,"Permission N3XV5",
                f"Autoriser {app_id} à utiliser : {cap} ?"
                )==QMessageBox.StandardButton.Yes:
                approved.append(cap)
        self.hub.grant(app_id,approved)
        self.status.setText("Installation confirmée. Permissions accordées : "
                            +(", ".join(approved) if approved else "aucune"))
        self.refresh()

    def launch_selected(self):
        app_id=self.selected()
        if not app_id:return
        records=self.hub.package_manager.list()
        record=records.get(app_id,{})
        if record.get("state")!="installed":
            QMessageBox.information(self,"Application","Installe d'abord le paquet Linux.")
            return
        manifest=record["manifest"]
        # Only fixed native paths: no search of user-controlled working directory.
        rel=manifest["executable"]
        if rel.startswith("bin/"):
            executable=Path("/usr")/rel
        else:
            executable=Path("/opt/n3xv5")/app_id/rel
        try:
            pid=self.hub.launch(app_id,executable)
            self.status.setText(f"Application {app_id} démarrée, PID {pid}, canal IPC privé ouvert.")
        except (PermissionError,ValueError,KeyError,OSError,NotImplementedError) as exc:
            QMessageBox.warning(self,"Lancement",str(exc))
