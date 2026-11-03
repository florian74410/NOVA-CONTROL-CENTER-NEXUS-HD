# Foundation v0.1 — architecture

## Goals
Native Linux/XFCE PySide6 app; an app catalog; unlimited instances in floating MDI windows; drag/drop; grid/cascade; persisted window geometry; dark blue NEXUS styling; in-process event bus.

## Scope and boundaries
- All four initial panels are demonstration interfaces. SSH, SFTP and Docker do **not** access a real server in v0.1.
- HTTPS panel uses Qt WebEngine if available; otherwise shows a clear unavailable message.
- Drag a catalog item onto workspace, or double-click to open another instance.
- Demo terminal button publishes `file.changed`; SFTP demo responds to it.
- Window positions are stored in XDG-style user config, not inside repository.
- Integration of arbitrary Linux third-party windows is not guaranteed.
- No background agent or server daemon is installed.

## Next milestones
v0.2: real SSH/PTTY terminal and key management; v0.3: SFTP explorer, change monitoring; v0.4: Docker via SSH; v0.5: synchronization dependency rules and validated refresh actions.

## Run (Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
nova-control-center
```
Qt WebEngine may require OS-specific shared libraries. Use Linux/X11 session for first MDI evaluations.

## Safety
Never put credentials in project JSON. Later remote actions require explicit permissions, host key verification and confirmation of destructive operations.
