# NOVA Core — OS user session, connection preloading, 7 protocols

The owner of a NOVA session is the **effective local application user**. If
that user belongs to the machine administrator group, the UI may indicate it,
but this is NOT an escalation of permissions or a root login.

## At session open
1. Read the signed-in local Linux account identity (name, UID, groups).
2. Read only that UID's private connection profiles from
   ~/.config/nova-control-center/connections-v2.json (mode 0600).
3. Preload metadata for FTP, SSH, HTTPS, MYSQL, SQLITE, SMTP, and TCP.
4. Identify whether the key path, SSH agent or keyring credentials are locally
   available; don't copy secret values to SQLite logs.
5. Make prepared connection handles available to hosted applications via
   ConnectionSessionCache. Apps then open sockets on demand, authenticate
   independently and may pool established connections when needed.
6. Re-read the profiles and credential availability when the session unlocks,
   or after the user changes a profile.

This is deliberately **not** eager network connection to every target server:
no unsolicited logins, resource exhaustion, or storing plaintext secrets.
The statuses READY_LOCAL / READY_TO_TEST / CREDENTIAL_REQUIRED /
MISSING_KEY / KEY_PERMISSIONS etc. describe local readiness, not successful
remote authentication.

## User interface
'Créer une connexion' is a native Core module reachable via top navbar,
left sidebar or command palette. It includes a separate configuration page
per protocol, a saved-profiles list, local readiness status and actions for
creating, editing, removing and selecting profiles.

## Security
- Connection credentials remain under the OS user's existing ssh-agent and
  system keyring. Private-key paths are not the private key itself.
- A local administrator's membership in sudo/wheel does not grant NOVA root.
- Connection credentials are resolved only when an app needs them.
- SQLite logs contain connection lifecycle and metadata, never credentials.
- ConnectionSessionCache is invalidated when NOVA is locked.
- Real network probes/connectors for all seven protocols will be separate
  adapters with timeouts and consent, not implied by metadata preloading.
