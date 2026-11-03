#!/usr/bin/env python3
"""NOVA Launcher v3 — one shortcut, graphical launcher or headless CLI.

Uses the standalone installer CLI, never runs downloaded code without a
validated distribution and SHA-256. Checking for updates never auto-installs.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

APP_ID="nova-control-center"
def home():
    return Path(os.environ.get("XDG_DATA_HOME",str(Path.home()/".local/share")))/"nova-suite"

def read_state(root):
    try:
        data=json.loads((root/"installed.json").read_text(encoding="utf-8"))
        if isinstance(data,dict):return data.get("apps",{})
    except (OSError,ValueError):
        pass
    return {}

def catalog(root):
    try:
        data=json.loads((root/"catalog.json").read_text(encoding="utf-8"))
        if data.get("schema")==1 and isinstance(data.get("apps"),list):
            return data["apps"]
    except (ValueError,OSError,AttributeError):
        pass
    return [{"id":APP_ID,"name":"NOVA Control Center","entrypoint":"nova-control-center",
             "manifest_url":None}]

def entry(app_id,root):
    state=read_state(root).get(app_id)
    if not state:return None
    target=root/"apps"/app_id/"current"/"bin"/"nova-control-center"
    return target if target.is_file() else None

def launch(app_id,root):
    executable=entry(app_id,root)
    if not executable:
        raise FileNotFoundError("NOVA is not installed. Use Installer.")
    # Popen detached: launcher can close while NOVA continues.
    subprocess.Popen([str(executable)],start_new_session=True,
                     stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL,close_fds=True)

def installer_command(root,args):
    script=root/"installer.py"
    if not script.is_file():raise FileNotFoundError("Installer CLI is missing")
    return [sys.executable,str(script),"--root",str(root),*args]

def check_update(app,root):
    # An optional release manifest is required. Until an official verified
    # release manifest is published, this reports 'not configured'.
    from urllib.request import urlopen,Request
    from urllib.parse import urlsplit
    url=app.get("manifest_url")
    if not url:return "Mises à jour non configurées"
    parts=urlsplit(url)
    if parts.scheme!="https" or parts.hostname not in (
        "github.com","raw.githubusercontent.com"):
        return "Source de mise à jour refusée"
    try:
        with urlopen(Request(url,headers={"User-Agent":"NOVA-Launcher/3"}),timeout=7) as response:
            if urlsplit(response.geturl()).scheme!="https":
                raise ValueError("Redirect insecure")
            raw=response.read(512*1024+1)
        if len(raw)>512*1024:raise ValueError("Manifest too large")
        data=json.loads(raw)
        if data.get("app_id")!=app["id"]:raise ValueError("Invalid app manifest")
        latest=data.get("version","?")
        current=read_state(root).get(app["id"],{}).get("version","non installée")
        return "À jour : "+str(latest) if current==latest else f"Version disponible : {latest} (actuelle : {current})"
    except (OSError,ValueError,TimeoutError,KeyError) as exc:
        return "Vérification impossible : "+str(exc)[:90]

def gui(root):
    try:
        import tkinter as tk
        from tkinter import ttk,messagebox,filedialog
    except ImportError:
        raise RuntimeError("Tkinter unavailable; use --launch or --status")
    root_window=tk.Tk()
    root_window.title("NOVA SUITE / LAUNCHER v3")
    root_window.geometry("610x370")
    root_window.minsize(500,320)
    root_window.configure(bg="#061523")
    style=ttk.Style(root_window)
    if "clam" in style.theme_names():style.theme_use("clam")
    style.configure("TFrame",background="#061523")
    style.configure("TLabel",background="#061523",foreground="#A3E8FF",font=("DejaVu Sans",11))
    style.configure("Header.TLabel",foreground="#F0FAFF",font=("DejaVu Sans",17,"bold"))
    style.configure("TButton",padding=(11,7),font=("DejaVu Sans",10))
    frame=ttk.Frame(root_window,padding=24)
    frame.pack(fill="both",expand=True)
    ttk.Label(frame,text="⬡  NOVA SUITE LAUNCHER",style="Header.TLabel").pack(anchor="w",pady=(0,9))
    ttk.Label(frame,text="Installateur CLI · Catalogue évolutif · Mises à jour").pack(anchor="w",pady=(0,15))
    apps=catalog(root)
    titles=[a.get("name",a["id"]) for a in apps]
    selected=tk.StringVar(value=titles[0])
    selector=ttk.Combobox(frame,values=titles,textvariable=selected,state="readonly")
    selector.pack(fill="x")
    status=tk.StringVar(value="Prêt")
    ttk.Label(frame,textvariable=status,wraplength=540).pack(anchor="w",pady=12)
    def current():
        index=max(0,selector.current())
        return apps[index]
    def refresh():
        a=current()
        installed=read_state(root).get(a["id"])
        status.set("Installée : "+installed["version"] if installed else "Non installée")
    def start():
        try:
            launch(current()["id"],root)
            status.set("Application démarrée")
        except Exception as exc:
            messagebox.showerror("NOVA",str(exc))
    def update_check():
        a=current()
        status.set("Vérification de la version disponible…")
        def job():
            result=check_update(a,root)
            if root_window.winfo_exists():
                root_window.after(0,lambda:status.set(result))
        threading.Thread(target=job,daemon=True).start()
    def run_installer(arguments):
        cmd=installer_command(root,arguments)
        # Never block GUI while wheel is installed; logs in temporary file.
        status.set("Installation CLI en cours…")
        def worker():
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=900)
            message=(result.stdout if result.returncode==0 else result.stderr).strip()[-500:]
            if root_window.winfo_exists():
                root_window.after(0,lambda:status.set(message or f"Code : {result.returncode}"))
        threading.Thread(target=worker,daemon=True).start()
    def install_local():
        path=filedialog.askopenfilename(title="Archive wheel NOVA",filetypes=[("Python wheel","*.whl")])
        if not path:return
        from tkinter import simpledialog
        version=simpledialog.askstring("Version","Numéro de version de cette archive")
        if not version:return
        digest=__import__("hashlib").sha256(Path(path).read_bytes()).hexdigest()
        confirm=messagebox.askyesno("Installer NOVA",
            f"Installer {version} depuis ce fichier local ?\nSHA-256 : {digest[:16]}…\n"
            "Le checksum doit correspondre à celui publié par l'éditeur.")
        if confirm:
            run_installer(["install","--app",current()["id"],
                           "--version",version,"--wheel",path,"--sha256",digest])
    def install_online():
        a=current()
        if not a.get("manifest_url"):
            messagebox.showinfo("NOVA","Aucune distribution officielle n'est encore publiée. "
                               "Installe une archive locale vérifiée.")
            return
        if messagebox.askyesno("NOVA","Télécharger et installer la version disponible ?"):
            run_installer(["update","--app",a["id"],"--manifest",a["manifest_url"]])
    actions=ttk.Frame(frame)
    actions.pack(fill="x",pady=12)
    for text,callback in (("▶ Démarrer",start),("↻ Vérifier MAJ",update_check),
                          ("⬇ Installer / MAJ",install_online),
                          ("◈ Wheel locale",install_local)):
        ttk.Button(actions,text=text,command=callback).pack(side="left",padx=(0,5))
    ttk.Button(frame,text="Actualiser l'état",command=refresh).pack(anchor="w")
    selector.bind("<<ComboboxSelected>>",lambda event:refresh())
    refresh()
    root_window.after(250,update_check)
    root_window.mainloop()

def main(argv=None):
    p=argparse.ArgumentParser(prog="nova-launcher")
    p.add_argument("--launch",action="store_true")
    p.add_argument("--status",action="store_true")
    p.add_argument("--check",action="store_true")
    p.add_argument("--app",default=APP_ID)
    p.add_argument("--root",type=Path)
    opts=p.parse_args(argv)
    base=opts.root.expanduser().resolve() if opts.root else home()
    if opts.status:
        print(json.dumps(read_state(base),indent=2))
    elif opts.check:
        a=next((x for x in catalog(base) if x["id"]==opts.app),None)
        if not a:raise ValueError("Application not in catalog")
        print(check_update(a,base))
    elif opts.launch:
        launch(opts.app,base)
    else:
        gui(base)
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except (ValueError,OSError,RuntimeError) as exc:
        print("NOVA launcher:",exc,file=sys.stderr)
        raise SystemExit(1)
