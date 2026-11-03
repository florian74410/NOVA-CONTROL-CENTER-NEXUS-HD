# Desktop host adapters

One Qt visual specification and one Core model, but OS-specific launchers,
signing, packaging and secret brokers:
- Windows/ : .exe installer, Win32/DPAPI/Credential Manager
- Linux/   : .deb, Secret Service, DBus, polkit
- macOS/   : signed .app inside .dmg, Keychain/launch services

All apps must be separate signed native packages and independent processes.
Native embedded child-window support varies by OS; external app windows are
a supported fallback rather than a universal embedding guarantee.

Existing Linux NOVA Control Center stays under `src/nova_control_center`
until it is migrated to this adapter layer and fully tested.
