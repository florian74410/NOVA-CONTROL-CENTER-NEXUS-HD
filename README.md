# NOVA CONTROL CENTER — NEXUS HD

Native Linux desktop multi-application workspace. **Foundation v0.1.0**.

## Features in this branch
- Qt 6 / PySide6 native interface and NEXUS HD-inspired dark blue QSS.
- Application catalog on the left, draggable onto a freely movable MDI desktop.
- Multiple independent instances of Terminal, SFTP, Docker and HTTPS panels.
- Window cascade and grid controls, plus geometry persistence.
- First local Qt signal-based event bus demonstrating module-to-module updates.
- No remote SSH/SFTP/Docker operations yet (explicit demo placeholders).

## Quick start
```bash
git clone -b work/foundation-v0.1-nexus-hd https://github.com/florian74410/NOVA-CONTROL-CENTER-NEXUS-HD.git
cd NOVA-CONTROL-CENTER-NEXUS-HD
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
nova-control-center
```

See [architecture notes](docs/ARCHITECTURE.md). NEXUS HD 0.8 exact production assets have not been imported yet; visual approval and asset licensing/source review are pending.
