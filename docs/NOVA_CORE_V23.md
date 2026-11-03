# NOVA CONTROL CENTER — Core 2.3

## Delivered
- CorePreferences JSON with schema validation, bounded retention, private atomic save.
- SQLite logbook (WAL), UTC timestamps, index by source and time, DEBUG/INFO/WARNING/ERROR/AUDIT, basic metadata redaction, query and pruning.
- Logs viewer popup accessible from left dock, main menu and Ctrl+K.
- SessionManager: ephemeral session ID, active-connection context, optional local PIN protected with scrypt salt and throttled retry, manual or idle lock.
- Core settings dialog: retention, max log records and idle-lock minutes; optional PIN creation.
- Existing Settings for appearance and Connections for SSH/API profiles remain independent.
- No application demos, and no real SSH or SFTP session automatically opened.

## Storage
- ~/.config/nova-control-center/core.json : non-secret Core preferences
- ~/.config/nova-control-center/lock.json : salt and scrypt verifier, never plaintext PIN
- ~/.config/nova-control-center/connections-v1.json : SSH/API endpoint metadata and key paths, no credentials
- ~/.local/share/nova-control-center/logs.sqlite3 : structured Core logs and audit
- ~/.config/nova-control-center/v21.json : layout/theme persisted by the existing shell

## Security boundaries
Local PIN is only a **convenience lock** for the NOVA UI, not a substitute for the Linux session password, full-disk encryption or server authentication. Use ssh-agent/Secret Service for credentials; never put passwords, access tokens or private SSH keys in SQLite. API/SSH access continues to use real authentication and host verification.

The retention cleaner deletes older logs and limits entries. Do not use it to claim immutable audit retention. For high-security auditing, a remote, append-only audit store is required. Log redaction is deliberately conservative; applications should publish structured non-secret metadata instead of raw HTTP headers/bodies.

## Run
Install from branch work/nexus-v2.3-config-logs-sessions using python3 -m venv, pip install -e ., nova-control-center. CI uses QT_QPA_PLATFORM=offscreen. XFCE visual verification is still pending.
