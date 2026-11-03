# N3XV5 DATA BRIDGE 1.0

## Contract for any peripheral CLI
Every CLI exposes a Unix socket (or another connector implementing the same Qt
signals). HUB owns rendering and caching; peripheral CLI owns command execution.

Request: `{"n3xv5":1,"id":"123","app":"example-cli","method":"data.get","params":{"names":["vps.status","vps.resources"]}}`

Response: `{"n3xv5":1,"id":"123","result":{"values":{"vps.status":{"value":"ONLINE","priority":1,"status":"ok"},"vps.resources":{"value":"...","priority":2,"status":"ok"}}}}`

NAME is the stable ID of a display value, not an arbitrary shell command.
Unknown IDs return `status:unknown`; individual failures return
`status:error`. A CLI may optionally expose `catalog.describe` with NAME,
description, unit, type, priority and actions.

## Shared cache
- Cache is namespaced by CLI app ID, shared by all its iFrames.
- TTL 60 seconds; stale values remain visible until successfully replaced.
- A missing value triggers asynchronous retrieval; pending requests deduplicate.
- Unlimited attempts over time, with a short delay between failures.
- Force refresh bypasses TTL and requests new data (without duplicating in-flight work).
- The socket is local; connection is nonblocking. Remote SSH command timeout is separate.
- Frame priority: 1x2 and 2x1 show P1, 3x3 shows P1+P2, 9x9 shows P1+P2+P3.

## Adding a new CLI
Implement the `data.get` JSONL contract in a CLI daemon and register a
connector with `CliCacheManager.register(app_id, connector)`. The Core and
GridEngine must not import peripheral implementation modules.

## Work remaining
The first IATB mapping returns text values from existing CLI commands.
Structured CPU/RAM/DISK parsing, action schemas and GUI action dialogs need
their own integration work. Runtime test/packaging is pending.
