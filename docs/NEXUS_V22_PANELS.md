# NOVA CONTROL CENTER — Shell panels V2.2

This is **Control Center**, not NEXUS Terminal. Its settings and connection
management belong to the host GUI. Terminal and Web Inspector remain installable
applications of the host, not internal copies.

## Host dialogs
- A frameless QPainter glass/PCB settings panel reachable from header, sidebar
  and Ctrl+K. Settings: glass opacity, animations, sidebar width, color theme,
  workspace restoration. Stored via Qt QSettings.
- A frameless Sessions dialog for named SSH public-key profiles and HTTPS API
  profiles. SSH files store **paths** to keys, never private-key material.
  SSH validation is non-interactive, uses known_hosts verification and does
  not disable authentication checks. The key-generation control copies an
  interactive ssh-keygen command: it does **not** generate or expose a passphrase
  in subprocess argv.
- API profiles store names and URLs without embedded secrets. Optional bearer
  token storage uses the system keyring. Tests use QNetworkAccessManager and do
  not follow redirects automatically, to avoid forwarding credentials.
- The main multiwindow host continues to start empty (no fake terminals).
- Web Inspector is specified as a future independent QWidget application.
  QtWebEngine for local inspection, optional mitmproxy only as an explicit
  opt-in tool. External web pages open using QDesktopServices.

## Developer/testing
`QT_QPA_PLATFORM=offscreen python -m pytest -q tests/test_control_panels.py`

This is an isolated feature branch until visual XFCE and security validation.
No system services, server settings or installed Terminal versions are changed.
