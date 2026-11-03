# IATB-CLI 1.3 FINAL — first N3XV5 peripheral mapping

Source: user-supplied `IATB-CLI.tar.gz` (README.md and `iatb` entrypoint).
The original CLI is a Linux Mint tool and remains an independently installable application.

The HUB adapter `nova_control_center.iatb_adapter` speaks N3XV5 CLI/1,
while internally invoking **documented IATB commands** as argument arrays,
without shell interpolation. CLI output is currently plain text, not invented
structured VPS measurements. This is a **read-only integration phase**.

## Categories
- Vitalité: `iatb vps status`, `resources`, `benchmark`, `doctor`, `gen1 status/resources`
- Services: `vps ps/audit`, `gen1 apps list/health`, `contabo instances`
- Journaux: `vps logs fundamental`
- Réseau: `gen1 caddy check`
- Actions: `doctor`, `git status`

## Execution
Launch the adapter with `python -m nova_control_center.iatb_adapter --n3xv5-request`.
Send a JSONL request for `catalog.describe` or one of the catalog methods.
The `iatb` executable must already be installed and on PATH, or set
`N3XV5_IATB_EXECUTABLE` to its absolute path.

Example:
```sh
printf '%s\n' '{"n3xv5":1,"id":"1","app":"iatb-cli","method":"catalog.describe","params":{}}' |
 python -m nova_control_center.iatb_adapter --n3xv5-request
```

`iatb start --debug`, `vps reboot/shutdown`, interactive SSH and tunnels
require specialized noninteractive execution semantics and explicit confirmations;
they are **not** exposed by this first adapter. `start --release` is explicitly
blocked in the source CLI.

The Qt sidebar currently uses provisional labels and a 2x3 placeholder tile.
The next UI milestone binds this catalog and command results to live widgets.
