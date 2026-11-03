# N3XV5 N0v4 HUD — migration without losing work

## Phase 0 (this PR)
- New standalone architecture root with testable contracts.
- Distinct host editions, native application packaging requirements.
- Stable profile data interchange metadata, never secrets.

## Phase 1: integrate existing Linux HUB (priority)
- Move, without rewriting from scratch, the stable NEXUS HD Qt shell,
  seven-protocol connection editor, SQLite logs and session state into
  Linux Desktop adapter.
- Replace legacy profile model with a versioned adapter/migrator;
  do not silently migrate credentials or delete original files.
- Implement non-forgeable authenticated IPC before admitting peripheral
  processes to use any connection.
- Verify startup/close/Settings/Connections stability under XFCE.

## Phase 2: independent peripheral packages
- NEXUS Terminal (Linux first), Remote Explorer SFTP, Network Inspector,
  GitHub Manager and IA-TB Dashboard each get standalone packages and
  manifest + authorization tests.
- Dependency references by SHA-256 and platform/ABI, offline install.
- Installer/update channels separately signed and with rollback.

## Phase 3: cross-platform
- Windows .exe native launcher and installer, keyring via DPAPI.
- macOS .app distributed through signed .dmg, Keychain.
- No assertions of Windows/macOS binary success before native OS CI.

## Phase 4: ISO
- Minimal Debian Linux boot image, splash/login, HUB kiosk-like session,
  networking and recovery terminal.
- UEFI/BIOS boot, QEMU tests, graphics fallback and offline installation.
- Persistent encrypted user profiles/log storage and dedicated OS update path.
- A bootable ISO must include the kernel and all necessary userland.
