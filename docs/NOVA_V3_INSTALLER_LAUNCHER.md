# NOVA 3.0 — CLI Installer, Launcher, Suite Downloader

## Architecture
- deploy/nova_installer.py: standard-library per-user CLI for installing verified release wheels into versioned Python environments. Commands: install, status, update, rollback, desktop.
- deploy/nova_launcher.py: lightweight Tk interface (with command-line fallback), desktop shortcut launcher, check on startup and user-confirmed updates. It doesn't install an update silently.
- deploy/nova_downloader.py: future suite catalog client that downloads each application's launcher and CLI from verified links; designed for 1 to N apps. The catalog currently contains only NOVA.
- deploy/bootstrap.py: stages the installer, launcher and catalog into ~/.local/share/nova-suite and creates ~/.local/bin/nova-launcher plus ~/.local/share/applications/nova-control-center.desktop (no sudo).

## Preview installation
Download the GitHub Actions artifact named nova-suite-v3-kit.zip from a successful v3 workflow. Extract and open terminal in nova-suite-v3-kit/. Then:
```bash
python3 bootstrap.py
cat SHA256SUMS.txt
python3 ~/.local/share/nova-suite/installer.py install \
  --app nova-control-center --version 3.0.0.dev0 \
  --wheel ./nova_control_center-3.0.0.dev0-py3-none-any.whl \
  --sha256 <published-64-char-wheel-digest>
nova-launcher
```
Check the actual generated wheel filename rather than assuming this example matches; the kit's README.txt provides a complete command with the correct SHA-256. The SHA-256 must be compared with trusted publisher information: a hash computed locally alone does not prove authenticity.

The launcher uses tkinter (python3-tk on Debian/Ubuntu/Mint); if not available, launch from CLI `python3 ~/.local/share/nova-suite/launcher.py --launch`.

## Future public updates
Release publication must provide an HTTPS manifest with:
```json
{
 "app_id": "nova-control-center",
 "version": "3.0.0",
 "wheel_url": "https://github.com/OWNER/REPO/releases/download/TAG/WHEEL.whl",
 "sha256": "64 lowercase hex characters"
}
```
and catalog.json must have its manifest_url set to the official pinned manifest URL. Until then the launcher accurately shows "Mises à jour non configurées" and does not download arbitrary code. Public releases require build provenance and protected signing in later work.

## Future 5-program suite
The catalog is a list of application descriptors: id, name, entrypoint, manifest_url, installer_url and installer_sha256, launcher_url and launcher_sha256. For every verified app, the downloader fetches its own installer and launcher into a separate folder. Do not silently execute those downloads. A later Suite Manager can display all five programs in the same interface and invoke their installers with separately validated contracts.

## Safety and rollback
- User-scoped install, never sudo.
- Per-release venv under ~/.local/share/nova-suite/apps/nova-control-center/versions/.
- Current symlink is atomically replaced after pip succeeds; failed installs are cleaned.
- Previous version pointer recorded in installed.json; use `rollback` to restore it.
- No shell execution of untrusted user input; URLs restricted to GitHub HTTPS endpoints.
- Wheel checksum verified before pip. Transitive PyPI dependencies are not yet fully locked/hashes pinned; this is a preview installer, not a hardened software supply chain.
- No service takeover or system-wide theme changes.
