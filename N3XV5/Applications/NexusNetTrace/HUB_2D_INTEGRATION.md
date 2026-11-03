# N3XV5 NetTrace 0.2 ↔ HUB 2.6 : 2D iFrame / Unix IPC

This integration is **Linux-first** and uses the existing native application manager.
The CLI remains its own process; the HUB alone creates Qt graphics.

## Architecture and message flow

```text
HUB Qt: NetTracePanel (toolbar + 9×9 GridView)
  │ user chooses probe/dns/tcp/tls/har/correlate
  ├─ N3XV5Host.launch("nexus-nettrace", [ "--hub-publish", command, args ])
  │   └─ LocalAppBroker creates one private AF_UNIX socketpair
  │      └─ N3XV5 NetTrace CLI 0.2: runs network diagnostic
  │         └─ PeripheralClient.request("nettrace.publish", {
  │               "command": "probe", "data": { redacted ... }
  │             })
  └─ LocalAppBroker checks installed app ID + declared capability + profile grant
      └─ Qt Signal → NetTracePanel.apply_report
          └─ NetTraceTile.paint → 9×9 grid, responsive detail tiers
```

IPC protocol is JSON Lines, max 8192 bytes per frame, and inherits the
existing per-process socket. The HUB does not open a TCP port, invoke an
HTTP proxy, sniff Firefox, or receive private keys.

The native installer must import **NetTrace CLI 0.2** (not legacy 0.1),
whose manifest declares `profile.read`, `connections.read`,
`nettrace.publish`. The end user must explicitly grant
`nettrace.publish` after installation.

## 9×9 iFrame layout contract

- Grid: exactly **9 columns × 9 rows**, snapping by integral cells.
- Frame interior margins: **3–10 px** within cell boundaries; never center
  the frame on a grid intersection or draw its border past cell edges.
- Minimum small format: **1×2** or **2×1**. **1×1 is prohibited**.
- Default medium: **2×3** cells.
- Large preset: **4×4** cells. Other sizes are allowed by drag.
- Drag the body to move, drag **bottom-right ↘** to resize and click
  **top-right ×** to close. Collisions and out-of-bounds moves are refused.
- Compact tier (under five cells): verdict and one highest-priority metric.
- Medium tier (5–11 cells): verdict plus latency, host, IP and method.
- Large tier (12+ cells, dimensions ≥3×3): DNS/TCP/TLS/TTFB phases,
  HTTP headers safely selected, diagnosis, and optionally HAR/VPS log rows.
- Cyan glass/PCB border, small red edge traces; no white rectangle or
  forced scrolling that hides the main verdict.

## Example: 502 on client ↔ Caddy ↔ VPS

Start the Linux HUB, open **NetTrace** in its toolbar, choose
`probe`, and enter `https://architecture.iatb.duckdns.org/api/overview`.
The HUB launches NetTrace as a separate app with inherited socket credentials.
NetTrace sends a request ID with the probe and publishes the redacted result.
The Qt widget shows the HTTP verdict immediately. Expand to see timings.
To cross-check with the VPS, export a JSONL proxy log containing the same
request ID, then choose `correlate` and select both files.

Do not assume 502 implies the upstream is down: verify server logs, reverse
proxy route, firewall, TLS and authentication on your own environment.

## Security and deployment

- No auto-accept of a message from an arbitrary process or socket pathname.
- No arbitrary commands / shell text from IPC are evaluated by the HUB.
- Active session can revoke socket channels at lock time.
- A capability listed in the app manifest is **not** equivalent to user approval.
- A screenshot or HAR may contain secrets; only redacted summary fields
  should be published. Network probes do not borrow browser cookies.
- The current event payload is a snapshot, **not** a continuous packet stream.
- `X-Request-ID` must be configured in the VPS proxy to correlate with logs.
- Windows/macOS adapters are separate future tasks; AF_UNIX is the Linux
  implementation.
