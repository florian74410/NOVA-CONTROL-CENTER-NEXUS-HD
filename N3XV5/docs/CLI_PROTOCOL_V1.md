# N3XV5 CLI Protocol v1 — Core / Peripheral contract

The HUB is the **only GUI renderer**. Peripherals are independent CLI executables; a standalone GUI is optional and never embedded.

## Transport
- A command is a short-lived subprocess launched with `--n3xv5-request` (configurable adapter arguments).
- One UTF-8 JSON object plus newline on **stdin**; one JSON object plus newline on **stdout**.
- Stderr is diagnostic only; stdout MUST contain only the protocol response.
- Max frame: 1 MiB. Each request has a unique string ID; response echoes it.
- Version field: `"n3xv5":1`. Core uses asynchronous QProcess; default timeout 10 seconds.
- A CLI may execute its own subcommands internally; HUB never interprets untrusted shell text.

Example request:
```json
{"n3xv5":1,"id":"42","app":"iatb-cli","method":"catalog.describe","params":{}}
```
Example response:
```json
{"n3xv5":1,"id":"42","result":{"categories":[{"id":"vitality","label":"Vitalité","commands":[{"method":"vps.health","label":"État VPS","kind":"metrics","refresh_ms":5000}]}]}}
```
Error:
```json
{"n3xv5":1,"id":"42","error":{"code":"UNAVAILABLE","message":"VPS unreachable"}}
```

## Catalog and UI
The `catalog.describe` response lists categories and commands. Each command defines `method`, `label`, `kind` (metrics, table, text, action, form), optional `params_schema`, and `refresh_ms`. The HUB builds all widgets. Clicking a sidebar category adds a **2x3 medium** tile to the first free 9x9 location. No fabricated IATB commands: map the actual IATB-CLI documentation before enabling real actions.

## Architecture
`NexusDesktop / GridView -> GridScene -> CliRunner(QProcess) -> CLI executable -> VPS`

The scene only changes geometry on resize; network/CLI requests never block the GUI thread. Core grid dimensions are 9x9; tiles can be dragged and snapped, resized in whole cells, and queried for valid placements.

## Migration
The previous N3XV5 IPC socketpair API remains intact for backward compatibility. The CLI request protocol is a **separate** adapter and does not require importing a peripheral's Python code. Future streaming CLI may use a persistent JSONL session, but v1 is one request per process for simplicity and crash isolation.

## Limits
IATB-CLI source/documentation not yet supplied; the sidebar is an integration entry and real commands remain unavailable until mapped. This is a development implementation, not a release-certified end-to-end IATB integration.
