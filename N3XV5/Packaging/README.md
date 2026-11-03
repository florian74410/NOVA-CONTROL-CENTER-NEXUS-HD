# Native packaging

Release matrix: windows-x64 .exe, linux-x64 .deb, macos-x64 .dmg,
macos-arm64 .dmg, live-linux-x64 .iso containing Linux packages.

Important separate concerns:
1. Build artifact and pinned runtime
2. Offline dependency cache and license notices
3. Signature, integrity, provenance/SBOM
4. Installer transactional updates/rollback
5. Noninteractive offline installation verified per platform
6. Portable profile export/import without secrets
7. Boot image OS updates and encrypted persistence

No cross-platform binary exists merely because shared Python sources compile.
