# NOVA CONTROL CENTER — NEXUS HD V2 / CYBERPCB

A native **Qt 6 / PySide6** modular Linux workspace with a dramatic Cyberpunk ElectroBlueNEON graphical shell. No Electron or HTML UI.

## What's new in V2

- Full visual redesign: glass panels, luminous double contours, biseled 45-degree corners, real PCB parallel routing, connected vias, moving electric light pulse, scalable vector N emblem and iconography.
- Header/navbar, left draggable app launcher, central floating multi-window desktop, compact 11pt status strip.
- Create several instances of the same app; drag/resize/minimize/maximize, mosaic/cascade, right-click menus and Ctrl+K command palette.
- ElectroBlueNEON / RougeERROR live switch; independent V2 persistence of layout and palette.
- Four local functional demonstration widgets (Terminal/Explorer/Widget Lab/NEXUS Event Monitor); simulated file-change notifications through the local event bus.

**Important:** V2 is a visual foundation, not a remote administration release. SSH/SFTP/Docker are not connected. The three source image boards informed the vector renderer, but are not yet sliced and embedded as pixel-perfect graphical sprites.

## Install on Linux Mint XFCE

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip libxcb-cursor0 libegl1 libopengl0
git clone -b work/nexus-hd-v2-cyberpcb https://github.com/florian74410/NOVA-CONTROL-CENTER-NEXUS-HD.git
cd NOVA-CONTROL-CENTER-NEXUS-HD
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
nova-control-center
```

[Implementation details](docs/NEXUS_V2.md). Testing: `QT_QPA_PLATFORM=offscreen pytest -q tests/test_nexus_v2.py`.
