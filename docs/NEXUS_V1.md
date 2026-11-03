# NOVA CONTROL CENTER — NEXUS HD V1

## Scope delivered
- Full Qt 6 / PySide6 desktop shell, no Electron, no web frontend.
- Top navbar (55px); left catalog, draggable and resizable via QSplitter.
- Central QMdiArea with multiple independent applications, custom header controls, QSizeGrip resize handle, grid/cascade.
- Slim bottom status strip (30px overall, text set to 11pt normal).
- Two switchable NEXUS-inspired theme palettes, custom PCB visual language and neon QSS styling.
- Context menu, Ctrl+K command palette, tooltip affordances, action shortcuts.
- Demo Terminal, Explorer, Widget Lab and Event Monitor, with a working local Qt signal bus.
- Workspace restore and theme persistence in ~/.config/nova-control-center/v1.json.

## Explicit limitations
- GUI uses Qt painted/style-based assets based on the 3 reference sheets. The detailed binary sprite sheets themselves are not committed to the repository by this source-only update.
- Existing source image sprites are not embedded as controls, because labels and layout are baked into the images and not nineslice-ready.
- SSH / SFTP / Docker connections and untrusted third-party app loading are **not available** in V1.
- Native embedding of arbitrary external processes is not promised.
- Qt GUI runtime testing requires a machine with PySide6 and display; the code was not executed on Linux Mint XFCE in the authoring environment.

## Run from repository
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
nova-control-center
```
To start the V1 explicitly:
```bash
python -m nova_control_center.nexus_v1
```

## Next: application SDK
Installable Qt modules must expose a QWidget factory, signed/trusted source, unique manifest ID, and should subscribe to a scoped event bus rather than import global desktop state.
