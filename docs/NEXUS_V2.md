# NOVA CONTROL CENTER — NEXUS HD V2 CyberPCB

## Scope
Native Linux application in Python / PySide6 (Qt6). A full visual redesign of V1: vector-drawn glass panels, real 45° cut corners, parallel PCB tracks/vias, glow edges, light sweeps, NEXUS vector N logo, icon-first navigation, custom title bars and window actions, drag/drop application catalog, status bar 11 pt, two palettes, context menus, Ctrl+K command palette, restore/save.

The V2 renderer recreates the visual grammar of the supplied blue neon UI boards as scalable Qt code. Exact source board PNG files (with baked text and other sheet elements) are not used as window controls; they must be separated and cleaned before being production 9-slice resources. Thus appearance may differ from the generated illustration.

Four demo panels only (Terminal preview / file explorer preview / widget lab / event monitor). NO real network connections and NO arbitrary third-party application embedding. No fake connectivity claims.

## Launch
\`\`\`bash
sudo apt install -y python3-venv python3-pip libxcb-cursor0 libegl1 libopengl0
git clone -b work/nexus-hd-v2-cyberpcb https://github.com/florian74410/NOVA-CONTROL-CENTER-NEXUS-HD.git
cd NOVA-CONTROL-CENTER-NEXUS-HD
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
nova-control-center
\`\`\`

Keyboard: Ctrl+K. Double-click sidebar app to create more instances. Drag catalog items onto the bureau. Right-click the desktop for arrangement and opening. Top toolbar gives tile/cascade/save/theme. Window headers support drag/minimize/maximize/close; bottom-right grips resize.

Stored state is \`~/.config/nova-control-center/v2.json\`, separate from V1. This is a review release, not a production-ready app SDK.

## Performance
PCB geometry is drawn at Qt paint time; no giant stretched sheet images. Only the top navbar has a lightweight 64ms pulse while visible. Embedded browser/remote services not launched. Animations can be disabled in a following settings module.
