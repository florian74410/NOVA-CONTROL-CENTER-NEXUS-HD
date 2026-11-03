# NOVA CONTROL CENTER — V2 NEXUS NOVA HD

## Real native implementation
V2 uses PySide6 Qt6 and QPainter for scale-independent chrome: chamfered window borders, embedded PCB routing and via nodes, multiple glow strokes, inner glass layers, active top-edge light sweep, and a vector icon library rendered from inline SVG paths.

### Framework and features
- 79px responsive top toolbar with logo, navigation and workspace actions
- Adjustable left app catalog (QSplitter)
- Freeform QMdiArea with draggable/minimizable/maximizable/resizable subwindows
- Multiple simultaneous Qt widget instances via a catalog, drag and drop or command palette
- Thin 33px total status strip with standard 11pt font
- Native context menu + Ctrl+K command launcher
- ElectroBlueNEON / RougeERROR palette switching
- Incremental active-window neon sweep (20fps, pausible)
- Workspace state persisted in ~/.config/nova-control-center/v2.json
- Demonstration apps: Terminal UI, SFTP tree, real local CPU/RAM/SSD usage, Widget Lab
- Event bus demonstration: Terminal publishes -> Explorer responds

## Current boundaries
- SSH/SFTP are **demonstration-only**. They do not connect remotely.
- Linux monitoring uses actual /proc and statvfs data. CPU initial value takes two refreshes.
- Mock browser windows, fake connection status and invented server metrics are intentionally omitted.
- Source artwork from provided sheets acts as a visual reference, **not** as clickable bitmaps. Real layout and controls are Qt-rendered; PNG pack integration remains future work.
- On XFCE, check high-DPI Qt scaling, translucency and resized MDI behavior against actual window-manager conditions.

## Try on Linux Mint XFCE
```bash
sudo apt install python3-venv python3-pip libxcb-cursor0
git clone -b work/nexus-v2-renderer https://github.com/florian74410/NOVA-CONTROL-CENTER-NEXUS-HD.git
cd NOVA-CONTROL-CENTER-NEXUS-HD
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
nova-control-center
```

## Tests
`QT_QPA_PLATFORM=offscreen python -m pytest -q tests/test_nexus_v2.py`
