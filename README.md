# NOVA CONTROL CENTER — NEXUS HD V2 (Full Qt)

**Native Linux Qt6 / PySide6 desktop shell** in the ElectroBlueNEON and RougeERROR design language.

## V2 UI development
- Scalable vector-drawn chamfered glass frames with PCB routes, vias and neon glow.
- Reusable SVG vector icon library.
- Rich desktop with four local Qt demonstration applications and multiple instances.
- Left application dock: double click or drag onto desktop.
- Freeform draggable windows, resize handles, minimize/maximize/close.
- Top navigation / grid / cascade / save and thin 11pt status strip.
- Theme switching, animated light sweep on active windows, toggleable.
- Ctrl+K command launcher, context menus and layout persistence.
- Monitored local Linux CPU/RAM/disks through /proc and statvfs — no fictitious production metrics.

## Try on Linux Mint XFCE

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip libxcb-cursor0
git clone -b work/nexus-v2-renderer https://github.com/florian74410/NOVA-CONTROL-CENTER-NEXUS-HD.git
cd NOVA-CONTROL-CENTER-NEXUS-HD
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
nova-control-center
```

The V2's SSH and SFTP windows are **local visual demonstrations**, not working remote-access clients. No server is contacted. The supplied three asset boards are the visual reference; the Qt renderer rebuilds scalable shapes rather than embedding fixed-size PNG sheets.

For details, read [docs/NEXUS_V2.md](docs/NEXUS_V2.md). The V2 remains a development branch until Linux XFCE visual testing is complete.
