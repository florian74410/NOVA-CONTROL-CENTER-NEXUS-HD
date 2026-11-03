# ISO mode — bootable N3XV5 mini Linux

The Live ISO includes its **own Linux kernel and base operating system**.
Build staging has already begun at `deploy/live_iso/build_live_iso.py`.
This module holds future boot tests, offline OS snapshot and BIOS/UEFI
compatibility work. No ISO image is asserted to exist yet.

Profiles, keys and passwords must never be baked into the ISO.
Persist profile data to a separately provisioned encrypted volume/virtual disk.
Keep a repair console even if the N3XV5 graphical shell fails.
