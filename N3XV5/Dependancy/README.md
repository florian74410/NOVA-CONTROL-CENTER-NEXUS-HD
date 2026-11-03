# N3XV5 shared dependency storage

A single **content-addressed artifact cache** per platform/ABI. Do not put
all applications in a shared Python site-packages: their runtimes must remain
isolated. Applications bring missing packages into the common store only after
cryptographic checksum and publisher verification.

Layout proposal:
- Common/<platform>/<abi>/sha256/<digest> : immutable downloaded assets
- Apps/<app-id>/<version>/<platform>/ : runtime pointers and manifests
- Locks/ : versioned, pinned dependency references
- Licenses/ : notices required for redistributed components

No native dependencies are committed to this folder yet. The old root
`Dependancy/` remains an initial offline wheel catalog and documentation.
