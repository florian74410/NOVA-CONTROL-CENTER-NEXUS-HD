# N3XV5 N0v4 HUD — Fresh Multi-platform Foundation

**N3XV5 N0v4 HUD** is the official name of the entire suite.

This directory is the **new architecture root**, intentionally separate from
legacy `src/nova_control_center` and `deploy` during migration.
Nothing in the existing Linux application has been removed.

## Product editions

| Edition | Host | Distribution |
| --- | --- | --- |
| HUB Desktop Windows | Windows 10/11 (x64) | Portable runtime + .exe installer |
| HUB Desktop Linux | Linux x86_64 (Mint/Ubuntu target) | Portable runtime + .deb |
| HUB Desktop macOS | macOS Intel/Apple Silicon | .app in .dmg |
| HUB Live | Minimal Linux with its own kernel/OS | Bootable .iso |

The peripherals are **independent processes and native platform packages**
(.exe, .deb, or .dmg/.app), not dynamically imported scripts into the HUB.
Each app registers an identity, its executable entrypoint, a platform target,
a capabilities list and the suite IPC protocol version.

## Architecture

```text
N3XV5/
├── Core/                     # platform-neutral Python model
│   └── n3xv5_core/
│       ├── contracts.py      # application manifests / platform targets
│       ├── suite.py          # installable app registry / compatibility
│       └── profile.py        # cross-app profile metadata model
├── Desktop/                  # future native Qt HOST builds
│   ├── Windows/
│   ├── Linux/
│   └── macOS/
├── LiveISO/                  # boot image builder and boot tests
├── Applications/             # app descriptors; no fake packages
├── Dependancy/               # shared content-addressed downloads
├── SDK/                      # future authenticated local IPC protocol
├── Packaging/                # distribution recipes; not binaries
├── docs/
└── tests/
```

## Strict contracts

- A single suite profile identifier is shared across all authorized apps.
- App authorization **must** be verified by the HUB per operation. A profile
  descriptor is not proof of login, and no OS UID is a privilege escalation.
- SSH credentials, database passwords and API tokens never enter application
  manifests, global JSON profiles or log files.
- The HUB uses a versioned local IPC protocol and binds the app's process
  identity before issuing short-lived app session capabilities. IPC/SSO
  implementation is **not yet complete**.
- Each native app carries an embedded runtime and its missing dependencies,
  while artifacts may be cached centrally by checksum and ABI/platform.
- The installer never loads arbitrary Python source from a manifest.
- The same Core and profile schema work on all platforms, but credentials
  are resolved through the OS-appropriate credential store.
- The bootable ISO includes a Linux OS; it is not a bare-metal Qt executable.

## Development status

The foundation below contains enforceable **data contracts and tests**, not
working Windows or macOS builds, finished SSO, or a bootable ISO.
Legacy Control Center (Linux Qt) remains the functioning development UI.
Migration into this root happens in separate reviewed steps.

The existing `Dependancy/` is kept as the transitional shared asset catalog.
The new `N3XV5/Dependancy/` describes the long-term multi-OS cache contract.
