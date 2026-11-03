# NOVA CONTROL CENTER — NEXUS HD 2.1

Native Linux / XFCE desktop shell built with **PySide6 / Qt 6**, featuring original ElectroBlueNEON and RougeERROR themes.

## V2.1 — graphical foundation only

- **No bundled fake applications.** Starts with an empty desktop and an empty application registry.
- Old demonstration terminals, explorers, monitors and their entrypoints have been removed from the V2.1 source.
- Frameless main window: custom NEXUS toolbar, minimize/maximize/close controls, drag via top frame, system-edge resize (where supported by XFCE/X11).
- Left navigation: contextual icon controls for the library, notifications, workspaces and preferences.
- Future installed application metadata is discovered through `~/.local/share/nova-control-center/Applications/Installed/*/manifest.json`; **no module code is imported without explicit future activation support**.
- NEXUS Full Qt PCB renderer, vector icons, amber/red/cyan notification states and user-customizable palettes.
- Context menu with optional original transparent PCB GIF (if generated asset is present).
- Twelve original procedurally generated transparent GIFs, six per theme; source generator: `tools/generate_nexus_gifs.py`.
- Compact bottom status bar and persisted themes, animation preference and workspace layout.
- Keyboard command palette: `Ctrl+K`. No network connections or server modifications.

## Install on Linux Mint XFCE

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip libxcb-cursor0

git clone -b work/nexus-v2.1-shell-assets \
  https://github.com/florian74410/NOVA-CONTROL-CENTER-NEXUS-HD.git \
  ~/NOVA-CONTROL-CENTER-V21

cd ~/NOVA-CONTROL-CENTER-V21
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
nova-control-center
```

To rebuild the GIF pack locally, install `Pillow` and run:

```bash
python -m pip install Pillow
python tools/generate_nexus_gifs.py
```

Generated GIFs live under `Assets/Generated/Animations/{ElectroBlueNEON,RougeERROR}/`. Qt's animated painter remains the default for high-frequency UI effects.

## Intended next milestone

The separate **NOVA App SDK** will provide a trusted install/activation workflow for native Qt modules. Merely listing a manifest does not activate executable code. All application instances will be represented as QWidget factories in a shared desktop context. We have deliberately left the app catalog empty rather than misleadingly displaying fake SSH/SFTP/Docker modules.

## Safety and platform notes

The GUI uses a frameless top-level window to suppress the unwanted grey XFCE title bar. Window moving and resizing use `startSystemMove`/`startSystemResize` when supported; behavior can differ between X11 compositors. To avoid conflicting with an existing NOVA installation, version 2.1 stores state in `~/.config/nova-control-center/v21.json`. The main app does not alter the XFCE panel or system window-manager theme.

The CI tests run in Qt offscreen mode. In-person interactive XFCE testing is still required.
