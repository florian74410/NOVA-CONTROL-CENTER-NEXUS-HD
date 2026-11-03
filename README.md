# NOVA CONTROL CENTER — NEXUS HD V1

Native **Full Qt / PySide6** Linux desktop workspace. Development branch: `work/nova-control-center-v1-fullqt`.

## Features
- Fixed neon navbar; resizable left-side application list; 30px compact status bar (11pt).
- Multi-window workspace with free placement, drag and drop, resize grip, minimize/maximize/close.
- Mosaïque, cascade, context menu and command palette `Ctrl+K`.
- ElectroBlueNEON / RougeERROR live palette switching.
- Save and restore workspaces and palette in `~/.config/nova-control-center/v1.json`.
- Four self-contained demonstration apps; NEXUS event bus test: Terminal demo publishes event, Explorer and Events receive it.
- No SSH/SFTP/Docker connection in this release. Do not use with production credentials.

## Installation (Linux Mint XFCE)
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip libxcb-cursor0
git clone -b work/nova-control-center-v1-fullqt https://github.com/florian74410/NOVA-CONTROL-CENTER-NEXUS-HD.git
cd NOVA-CONTROL-CENTER-NEXUS-HD
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
nova-control-center
```

See [V1 architecture and limitations](docs/NEXUS_V1.md).

This implementation reconstructs the neon interface in native Qt styles and scalable drawing, inspired by the three supplied UI design sheets. Their original bitmap files are not yet in GitHub and were not split into production 9-slice assets. The foundation is therefore a first functional visual implementation rather than a pixel-perfect reproduction. End-to-end GUI execution on Linux Mint XFCE is pending.
