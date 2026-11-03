# N3XV5 Phase 2–4 — HUB / sessions / native packages (Linux preview)

## 2. Existing Linux Qt HUB integrated

`nova_control_center.nexus_v21.MainWindow` keeps ElectroBlueNEON,
red PCB accents, notifications, settings, session PIN, SQLite logs, and
seven existing connection editors. Its Applications button now displays
the native-package manager. The shared N3XV5 code is installed from
`N3XV5/Core/n3xv5_core` in the same Qt distribution.

The profile remains tied to the active Linux account. We do **not**
migrate or copy secret credentials into the new universal profile.

## 3. Application authentication and sessions

`LocalAppBroker` launches a registered Linux native executable in its own
process, creates a private Unix socketpair and hands the child **only its
socket descriptor**. No public listening port, no reusable password or
session token on the command line. The child uses
`n3xv5_core.ipc.PeripheralClient` to communicate.

Methods in IPC v1:
- `hello` and `session.ping`: active channel only;
- `profile.info`: requires both app-declared and user-approved `profile.read`;
- `connections.list` and `connection.describe`: require
  `connections.read`. Only ID, label and protocol; never secret or private
  key contents.

A locked session revokes outstanding channels. Reunlocking does not
automatically reauthorize existing child sockets: new app launch is needed.
The initial OS login is the basis of local identity and the optional HUB PIN
is a convenience lock; it does not become an OS authentication provider.
`N3XV5_IPC_FD` identifies only a private inherited descriptor, not a token.

**Limit:** this is a Linux-first, HUB-launched app IPC proof of integration,
not a security boundary against a malicious process already running under
the same Linux account (which may use ptrace/proc depending on OS settings).
Future hardening: Unix peer credentials, sandboxing, signed package identity,
systemd services/sockets; Windows named pipes/DPAPI, macOS Keychain/XPC
adapters are not implemented.

## 4. Native application manager + Dependancy

The Qt Applications panel accepts a local JSON manifest and the matching
`.deb` package, verifies their filename/target SHA-256, and places them
into private per-app staging. For missing dependencies it requests a local
`Dependancy` folder and imports files **by pinned SHA-256** into the common
cache. No network dependency acquisition occurs at application launch.

The user must explicitly approve:
1. Package import and declared capability list;
2. OS installation of the verified local package via `pkexec apt-get`;
3. Each requested application permission *after* installation success.

Package state is `staged` until apt-get reports success. An imported
package is not automatically executed. Each app gets a separate Unix process
and a private IPC channel. No arbitrary Python code from the manifest is
loaded by the HUB.

**Security limitation:** a SHA-256 stored in a manifest from the same source
does **not** establish publisher authenticity. Only import packages from
sources you trust. Signed manifests/installers and package provenance
verification must be added before enabling untrusted public catalogs.

**Platform limitation:** .exe and .dmg are recognized by the new common
manifest contract, but only the Linux .deb installation adapter has been
implemented. It is not appropriate to claim Windows/macOS builds already
work.

**Current version**: `2.5.0.dev0` development snapshot (no merge to main).
