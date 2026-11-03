# IPC/SSO SDK — v1 contract

Planned authenticated process-to-HUB local IPC (Unix sockets on Linux/macOS,
named pipes on Windows), versioned message schema and per-operation capability
checks. Never pass a reusable login token through command-line arguments.
A manifest's profile_id alone is not authentication.

Actual IPC transport, OS process peer verification, session issuance,
expiry/revocation, and remote credential broker remain TODO and require tests
before registering external apps as authenticated.
