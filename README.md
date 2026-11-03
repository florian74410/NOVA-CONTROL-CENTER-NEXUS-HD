# NOVA CONTROL CENTER — NEXUS HD V2 / CYBERPCB

A native **Qt 6 / PySide6** modular Linux workspace with a dramatic Cyberpunk ElectroBlueNEON graphical shell. No Electron or HTML UI.

## What's new in V2

- Full visual redesign: glass panels, luminous double contours, biseled 45-degree corners, real PCB parallel routing, connected vias, moving electric light pulse, scalable vector N emblem and iconography.
- Header/navbar, left draggable app launcher, central floating multi-window desktop, compact 11pt status strip.
- Create several instances of the same app; drag/resize/minimize/maximize, mosaic/cascade, right-click menus and Ctrl+K command palette.
- ElectroBlueNEON / RougeERROR live switch; independent V2 persistence of layout and palette.
- Four visual-only demonstration panels (Design Lab / 3D Reactor / PCB Routing / Widget Kit), without mock SSH or remote operations. Optional Qt Quick 3D reactor, with safe 2D fallback.

**Important:** V2 is a visual foundation, not a remote administration release. SSH/SFTP/Docker are not connected. The supplied reference image and source boards informed the vector renderer, but are not yet sliced and embedded as pixel-perfect graphical sprites.

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

## Optional Qt Quick 3D

The application defaults to a light 2D reactor preview, suitable for XFCE and systems without 3D acceleration. Enable the Qt Quick 3D scene with:

```bash
NOVA_ENABLE_3D=1 nova-control-center
```

Qt Quick 3D and the appropriate system OpenGL drivers must be available; the main UI remains Qt Widgets. If the scene cannot initialize, the reactor panel falls back to 2D. All panels are visual UI samples, not connected applications.
