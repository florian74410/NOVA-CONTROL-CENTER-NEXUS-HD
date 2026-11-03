"""NOVA update manager: read official GitHub releases and verify DEB SHA-256.

All downloads are opt-in. A successful release lookup is not an update until
the version is newer. The UI never silently runs privileged commands.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QMessageBox
from .control_panels import NovaDialog

OWNER="florian74410"
REPO="NOVA-CONTROL-CENTER-NEXUS-HD"
API=f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
RELEASE_PAGE=f"https://github.com/{OWNER}/{REPO}/releases"
CURRENT="2.4.1-dev0"
MAX_DEB=550*1024*1024
ASSET=re.compile(r"^NOVA-Control-Center_[0-9][0-9A-Za-z.+~_-]*_amd64\.deb$")
def version_key(value):
    nums=[int(n) for n in re.findall(r"\d+",str(value))[:3]]
    while len(nums)<3:nums.append(0)
    return tuple(nums)
def newer(remote,local=CURRENT):
    return version_key(remote)>version_key(local)
def allowed_asset(url):
    s=urlsplit(url)
    return (s.scheme=="https" and not s.username and not s.password
            and s.hostname in {"github.com","objects.githubusercontent.com",
                                "release-assets.githubusercontent.com"})
def request_json():
    with urlopen(Request(API,headers={
        "User-Agent":"NOVA-Control-Center-Updater/2.4.1",
        "Accept":"application/vnd.github+json"}),timeout=12) as response:
        if urlsplit(response.geturl()).scheme!="https":
            raise ValueError("Unsafe release API redirect")
        data=response.read(512*1024+1)
        if len(data)>512*1024:raise ValueError("Release response too large")
    release=json.loads(data)
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("The latest GitHub release is not stable")
    version=str(release.get("tag_name","")).lstrip("vV")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-.][a-zA-Z0-9.]+)?",version):
        raise ValueError("Release version is invalid")
    assets=release.get("assets",[])
    deb=next((x for x in assets if ASSET.fullmatch(x.get("name",""))),None)
    sums=next((x for x in assets if x.get("name")=="SHA256SUMS.txt"),None)
    if not deb or not sums:raise ValueError("No .deb and SHA256SUMS.txt assets")
    for a in (deb,sums):
        if not allowed_asset(a.get("browser_download_url","")):
            raise ValueError("Release asset URL refused")
    return {"version":version,"deb":deb["browser_download_url"],
            "name":deb["name"],"sums":sums["browser_download_url"],
            "page":release.get("html_url",RELEASE_PAGE)}

def download_limited(url,max_bytes):
    if not allowed_asset(url):raise ValueError("Untrusted asset URL")
    with urlopen(Request(url,headers={"User-Agent":"NOVA-Updater/2.4.1"}),
                 timeout=40) as response:
        if not allowed_asset(response.geturl()):
            raise ValueError("Unsafe asset redirect")
        chunks=[]
        total=0
        while True:
            chunk=response.read(1024*1024)
            if not chunk:break
            total+=len(chunk)
            if total>max_bytes:raise ValueError("Download size exceeded")
            chunks.append(chunk)
    return b"".join(chunks)

def verified_deb(release,target):
    sums=download_limited(release["sums"],256*1024).decode("utf-8")
    expected=None
    for line in sums.splitlines():
        parts=line.strip().split()
        if len(parts)==2 and parts[1].lstrip("*")==release["name"] and re.fullmatch("[a-fA-F0-9]{64}",parts[0]):
            expected=parts[0].lower()
    if not expected:raise ValueError("Release SHA-256 entry missing")
    if not allowed_asset(release["deb"]):raise ValueError("Untrusted DEB")
    sha=hashlib.sha256()
    total=0
    with urlopen(Request(release["deb"],headers={"User-Agent":"NOVA-Updater/2.4.1"}),
                 timeout=50) as response:
        if not allowed_asset(response.geturl()):raise ValueError("Unsafe redirect")
        with target.open("wb") as out:
            target.chmod(0o600)
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                total+=len(chunk)
                if total>MAX_DEB:raise ValueError("DEB exceeds size limit")
                sha.update(chunk)
                out.write(chunk)
    if sha.hexdigest()!=expected:
        target.unlink(missing_ok=True)
        raise ValueError("Release DEB checksum mismatch")
    return target

class UpdateWorker(QThread):
    checked=Signal(object)
    downloaded=Signal(str)
    failed=Signal(str)
    def __init__(self,mode,release=None,target=None,parent=None):
        super().__init__(parent)
        self.mode=mode
        self.release=release
        self.target=target
    def run(self):
        try:
            if self.mode=="check":self.checked.emit(request_json())
            else:self.downloaded.emit(str(verified_deb(self.release,self.target)))
        except Exception as exc:
            self.failed.emit(str(exc)[:350])

class UpdateDialog(NovaDialog):
    def __init__(self,palette,parent=None):
        super().__init__("NOVA / MISES À JOUR EN LIGNE",palette,parent)
        self.setMinimumSize(560,330)
        self.resize(670,370)
        self.release=None
        self.worker=None
        self.download_dir=None
        self.downloaded=None
        self.message=QLabel("Source : GitHub Releases / dépôt officiel NOVA")
        self.message.setWordWrap(True)
        self.content.addWidget(self.message)
        self.version=QLabel("Version installée : "+CURRENT)
        self.content.addWidget(self.version)
        self.content.addStretch()
        self.check_button=QPushButton("↻ Vérifier les mises à jour")
        self.check_button.clicked.connect(self.check)
        self.content.addWidget(self.check_button)
        self.download_button=QPushButton("⬇ Télécharger et vérifier le .deb")
        self.download_button.clicked.connect(self.download)
        self.download_button.setEnabled(False)
        self.content.addWidget(self.download_button)
        self.install_button=QPushButton("Installer la mise à jour vérifiée")
        self.install_button.clicked.connect(self.install)
        self.install_button.setEnabled(False)
        self.content.addWidget(self.install_button)
    def _worker(self,mode,release=None,target=None):
        if self.worker is not None and self.worker.isRunning():return
        self.check_button.setEnabled(False)
        self.download_button.setEnabled(False)
        worker=UpdateWorker(mode,release,target,self)
        self.worker=worker
        worker.checked.connect(self.on_checked)
        worker.downloaded.connect(self.on_downloaded)
        worker.failed.connect(self.on_failure)
        worker.finished.connect(self.on_finished)
        worker.start()
    def check(self):
        self.message.setText("Vérification HTTPS du dépôt GitHub…")
        self._worker("check")
    def on_checked(self,release):
        self.release=release
        self.version.setText("Version installée : "+CURRENT+"  |  Release : "+release["version"])
        if newer(release["version"]):
            self.message.setText("Mise à jour officielle disponible. Téléchargement après confirmation.")
            self.download_button.setEnabled(True)
        else:
            self.message.setText("Aucune version stable plus récente publiée.")
    def download(self):
        if not self.release or not newer(self.release["version"]):return
        answer=QMessageBox.question(self,"Téléchargement",
            "Télécharger la mise à jour officielle et vérifier son SHA-256 ?")
        if answer!=QMessageBox.StandardButton.Yes:return
        # Keep the file on disk while pkexec/apt-get processes it.
        import os
        base=Path(os.environ.get("XDG_CACHE_HOME",str(Path.home()/".cache")))/"nova-control-center"/"updates"
        base.mkdir(mode=0o700,parents=True,exist_ok=True)
        base.chmod(0o700)
        target=base/self.release["name"]
        self.message.setText("Téléchargement et vérification SHA-256 en cours…")
        self._worker("download",self.release,target)
    def on_downloaded(self,path):
        self.downloaded=Path(path)
        self.install_button.setEnabled(True)
        self.message.setText("✓ Archive vérifiée. Installation facultative après confirmation.")
    def install(self):
        if not self.downloaded or not self.downloaded.is_file():return
        if QMessageBox.question(self,"Installer NOVA",
            "Installer le paquet .deb téléchargé via GitHub HTTPS et vérifié par SHA-256 ? "
            "Cette action nécessite les privilèges système.")!=QMessageBox.StandardButton.Yes:
            return
        # pkexec invokes apt-get without a shell and asks for authentication.
        import shutil
        if shutil.which("pkexec") is None:
            QMessageBox.warning(self,"Installation","pkexec indisponible : installer le .deb manuellement.")
            return
        try:
            subprocess.Popen(["pkexec","/usr/bin/apt-get","install","-y",
                              str(self.downloaded.resolve())],close_fds=True)
            self.message.setText("Installateur système lancé. Redémarre NOVA après installation.")
            self.install_button.setEnabled(False)
        except OSError as exc:
            QMessageBox.warning(self,"Installation",str(exc))
    def on_failure(self,error):
        self.message.setText("Vérification impossible : "+error)
    def on_finished(self):
        self.check_button.setEnabled(True)
        if self.release and newer(self.release["version"]) and self.downloaded is None:
            self.download_button.setEnabled(True)
    def reject(self):
        if self.worker is not None and self.worker.isRunning():
            self.message.setText("Opération en cours : ferme ce panneau après son achèvement.")
            return
        super().reject()
