"""N3XV5 NetTrace CLI — privacy-first network diagnostics for client/VPS.

Standalone Python >=3.10. Uses curl if available for browser-like timing.
Never captures decrypted traffic of other applications, HTTPS secrets,
request/response bodies or unapproved server logs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit, unquote

VERSION = "0.1.0"
MAX_HAR = 20 * 1024 * 1024
MAX_LOG = 20 * 1024 * 1024
MAX_ENTRIES = 5000
SAFE_HEADERS = {"content-type", "content-length", "server", "date",
                "cache-control", "access-control-allow-origin",
                "access-control-allow-methods", "access-control-allow-headers",
                "strict-transport-security", "x-request-id",
                "x-correlation-id", "traceparent", "cf-ray", "via",
                "location", "content-security-policy"}
TIMING_FIELDS = ("time_namelookup", "time_connect", "time_appconnect",
                 "time_pretransfer", "time_starttransfer", "time_total")
TRACE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
HTTP_URL = ("http", "https")


def safe_url(value: str) -> str:
    """Display host/path/query keys without leaking query secrets or credentials."""
    parts = urlsplit(value)
    if parts.scheme not in HTTP_URL or not parts.hostname:
        raise ValueError("Expected http:// or https:// URL with hostname")
    if parts.username or parts.password:
        raise ValueError("Credentials in URL are forbidden")
    if any(ch in value for ch in ("\n", "\r", "\x00")):
        raise ValueError("Invalid control character in URL")
    if parts.port is not None and not 1 <= parts.port <= 65535:
        raise ValueError("Invalid port")
    # Do not log path segments that look like query-style secrets.
    path = parts.path[:240]
    if re.search(r"(?:token|secret|password|apikey|api_key)[=/]", path, re.I):
        path = "/[REDACTED-PATH]"
    query = "&".join(k[:45] + "=[REDACTED]"
                     for k, _ in parse_qsl(parts.query, keep_blank_values=True)[:30])
    hostname = parts.hostname.lower()
    authority = hostname if ":" not in hostname else "[" + hostname + "]"
    if parts.port:
        authority += ":" + str(parts.port)
    return urlunsplit((parts.scheme, authority, path, query, ""))


def validate_url(value: str) -> str:
    safe_url(value)
    if len(value) > 2048:
        raise ValueError("URL too long")
    return value


def safe_header_map(raw_headers):
    """Allowlist only known operational headers, never Cookie/Authorization."""
    result = {}
    if isinstance(raw_headers, dict):
        pairs = raw_headers.items()
    else:
        pairs = ((x.get("name"), x.get("value")) if isinstance(x, dict) else (x[0], x[1])
                 for x in raw_headers
                 if isinstance(x, dict) or (isinstance(x, (tuple, list)) and len(x) == 2))
    for name, value in pairs:
        key = str(name or "").lower()
        if key not in SAFE_HEADERS:
            continue
        if key == "location":
            try:
                value = safe_url(str(value))
            except ValueError:
                value = "[REDACTED]"
        elif key in ("x-request-id", "x-correlation-id", "traceparent", "cf-ray"):
            if not TRACE_ID.fullmatch(str(value or "")):
                continue
        else:
            value = str(value).replace("\r", "").replace("\n", "")[:200]
        result[key] = value
    return result


def read_small_json(path: str, maximum: int):
    source = Path(path).expanduser()
    if not source.is_file() or source.stat().st_size > maximum:
        raise ValueError("Input missing or exceeds safety size limit")
    return json.loads(source.read_text(encoding="utf-8"))


def diagnostic_for(status: int | None, error: str | None = None, elapsed_ms: float | None = None):
    if error:
        return {
            "issue": error,
            "advice": {
                "dns": "Compare client DNS resolution with server A/AAAA records.",
                "tcp": "Check firewall, route and VPS listening port (ss -ltn).",
                "tls": "Verify certificate SAN, expiration, system clock and chain.",
                "timeout": "Check network path, reverse proxy and upstream logs.",
                "connection": "Inspect network, firewall and port on both ends.",
            }.get(error, "Inspect client/proxy/server logs with the correlation ID.")
        }
    status = int(status or 0)
    if status in (401, 403):
        return {"issue": "authentication_or_access", "advice": "Compare auth/session, proxy policy and origin ACL; do not export tokens."}
    if status == 404:
        return {"issue": "route_not_found", "advice": "Compare HTTP path, proxy location rules and backend route."}
    if status in (502, 503, 504):
        return {"issue": "gateway_or_upstream", "advice": "Correlate X-Request-ID with proxy and application logs; check upstream health and timeout."}
    if status >= 500:
        return {"issue": "server_error", "advice": "Use request ID to inspect backend error logs and trace."}
    if status >= 400:
        return {"issue": "client_request_error", "advice": "Review request method/headers, route and server validation."}
    if elapsed_ms is not None and elapsed_ms > 2000:
        return {"issue": "slow_response", "advice": "Compare DNS, TCP, TLS, TTFB and server processing duration."}
    return {"issue": "no_http_error_detected", "advice": "A successful HTTP status does not guarantee browser CORS or app-level success."}


def parse_header_file(path):
    """Keep only the final response block, never store raw header material."""
    headers = {}
    try:
        content = Path(path).read_text(encoding="iso-8859-1")
    except OSError:
        return headers
    for block in re.split(r"\r?\n\r?\n", content):
        if block.startswith("HTTP/"):
            headers = {}
            for line in block.splitlines()[1:]:
                if ":" in line:
                    name, value = line.split(":", 1)
                    headers[name.strip()] = value.strip()
    return safe_header_map(headers)


def probe(url: str, method: str = "GET", timeout: float = 15, curl_binary: str = "curl",
          request_id: str | None = None, origin: str | None = None):
    """Inspect only a direct explicit HTTP request, no browser interception."""
    import tempfile
    validate_url(url)
    method = method.upper()
    if method not in ("GET", "HEAD", "OPTIONS"):
        raise ValueError("Only read-oriented GET, HEAD or OPTIONS probes are allowed")
    if not 1 <= timeout <= 120:
        raise ValueError("Timeout must be between 1 and 120 seconds")
    if origin and ("\r" in origin or "\n" in origin or len(origin) > 255):
        raise ValueError("Invalid Origin")
    request_id = request_id or "n3xv5-" + uuid.uuid4().hex[:20]
    if not TRACE_ID.fullmatch(request_id):
        raise ValueError("Invalid correlation ID")
    if not shutil.which(curl_binary):
        raise RuntimeError("curl executable is required and must be bundled for an offline portable release")
    with tempfile.TemporaryDirectory(prefix="n3xv5-nettrace-") as temp:
        headers_file = str(Path(temp) / "headers.txt")
        args = [curl_binary, "--silent", "--show-error",
                "--proto", "=http,https", "--proto-redir", "=http,https",
                "--max-time", str(timeout), "--connect-timeout", str(min(timeout, 8)),
                "--request", method, "--dump-header", headers_file,
                "--output", str(Path(temp) / "body.bin"),
                "--max-filesize", "2097152", "--write-out", "%{json}",
                "--header", "X-Request-ID: " + request_id,
                "--user-agent", "N3XV5-NetTrace/0.1",
                "--", url]
        if origin:
            args[-2:-2] = ["--header", "Origin: " + origin]
        started = time.monotonic()
        # PyInstaller modifies LD_LIBRARY_PATH for bundled Python libraries.
        # Restore the original loader path before invoking external curl.
        # Otherwise curl may fail to link libssl/libcurl in onefile builds.
        curl_env = os.environ.copy()
        if getattr(sys, "frozen", False):
            if "LD_LIBRARY_PATH_ORIG" in curl_env:
                curl_env["LD_LIBRARY_PATH"] = curl_env["LD_LIBRARY_PATH_ORIG"]
            else:
                curl_env.pop("LD_LIBRARY_PATH", None)
        try:
            result = subprocess.run(args, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=timeout + 4,
                                    check=False, env=curl_env)
        except subprocess.TimeoutExpired:
            return {"target": safe_url(url), "request_id": request_id,
                    "method": method, "error": "timeout",
                    "diagnosis": diagnostic_for(None, "timeout")}
        elapsed = round((time.monotonic() - started) * 1000, 2)
        try:
            data = json.loads(result.stdout.decode("utf-8").strip())
        except (ValueError, UnicodeDecodeError):
            data = {}
        times = {}
        for field in TIMING_FIELDS:
            try:
                value = float(data.get(field, 0))
                times[field.removeprefix("time_") + "_ms"] = round(value * 1000, 2)
            except (ValueError, TypeError):
                pass
        status = int(data.get("http_code") or 0)
        fail = None
        if result.returncode != 0:
            fail = {6: "dns", 7: "tcp", 28: "timeout", 35: "tls",
                    51: "tls", 60: "tls", 52: "connection", 56: "connection",
                    63: "response_size_limit"}.get(result.returncode, "curl_error")
        output = {
            "target": safe_url(url), "request_id": request_id,
            "method": method, "status": status,
            "http_version": str(data.get("http_version", ""))[:12],
            "remote_ip": str(data.get("remote_ip", ""))[:64],
            "duration_ms": round(float(data.get("time_total") or elapsed / 1000) * 1000, 2),
            "timings_ms": times, "size_download_bytes": int(data.get("size_download") or 0),
            "tls_verify_result": data.get("ssl_verify_result"),
            "response_headers": parse_header_file(headers_file),
            "error": fail, "curl_exit_code": result.returncode,
        }
        output["diagnosis"] = diagnostic_for(status, fail, output["duration_ms"])
        return output


def probe_stdlib(url: str, method: str = "GET", timeout: float = 15,
                 request_id: str | None = None, origin: str | None = None):
    """Portable HTTP/1.1 fallback: Python stdlib, TLS verified, no curl needed.

    This is an active direct request, not a passive browser sniff or proxy.
    Redirects are reported rather than followed. No body is retained.
    """
    import http.client
    validate_url(url)
    method = method.upper()
    if method not in ("GET", "HEAD", "OPTIONS"):
        raise ValueError("Only GET, HEAD and OPTIONS supported")
    if not 1 <= timeout <= 120:
        raise ValueError("Timeout must be between 1 and 120")
    if origin and ("\r" in origin or "\n" in origin or len(origin) > 255):
        raise ValueError("Invalid Origin")
    parts = urlsplit(url)
    host = parts.hostname
    port = parts.port or (443 if parts.scheme == "https" else 80)
    request_id = request_id or "n3xv5-" + uuid.uuid4().hex[:20]
    if not TRACE_ID.fullmatch(request_id):
        raise ValueError("Invalid request ID")
    result = {"target": safe_url(url), "request_id": request_id,
              "method": method, "engine": "python-stdlib-http1",
              "http_version": "1.1", "remote_ip": "", "status": 0,
              "response_headers": {}, "timings_ms": {}, "error": None,
              "size_download_bytes": 0}
    start = time.monotonic()
    sock = None
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        dns_end = time.monotonic()
        result["timings_ms"]["namelookup_ms"] = round((dns_end-start)*1000,2)
        last_error = None
        for family,kind,proto,_,address in addresses:
            candidate = socket.socket(family,kind,proto)
            candidate.settimeout(timeout)
            try:
                candidate.connect(address)
                sock = candidate
                result["remote_ip"] = str(address[0])[:64]
                break
            except OSError as exc:
                last_error = exc
                candidate.close()
        if sock is None:
            raise ConnectionError("TCP connection refused or unreachable") from last_error
        tcp_end = time.monotonic()
        result["timings_ms"]["connect_ms"] = round((tcp_end-start)*1000,2)
        if parts.scheme == "https":
            context = ssl.create_default_context()
            sock = context.wrap_socket(sock,server_hostname=host)
            result["tls_version"] = sock.version()
        tls_end = time.monotonic()
        result["timings_ms"]["appconnect_ms"] = round((tls_end-start)*1000,2)
        authority = host if ":" not in host else "["+host+"]"
        if parts.port:
            authority += ":" + str(parts.port)
        target = (parts.path or "/") + ("?"+parts.query if parts.query else "")
        if any(c in target for c in ("\r","\n")):
            raise ValueError("Invalid request path")
        headers = [f"{method} {target} HTTP/1.1", f"Host: {authority}",
                   "Connection: close", "User-Agent: N3XV5-NetTrace/0.1",
                   "X-Request-ID: "+request_id]
        if origin:
            headers.append("Origin: "+origin)
        outgoing = ("\r\n".join(headers)+"\r\n\r\n").encode("utf-8")
        sock.sendall(outgoing)
        response = http.client.HTTPResponse(sock,method=method)
        response.begin()
        response_at = time.monotonic()
        result["timings_ms"]["starttransfer_ms"] = round((response_at-start)*1000,2)
        result["status"] = response.status
        result["response_headers"] = safe_header_map(response.getheaders())
        total = 0
        while total <= 2*1024*1024:
            chunk = response.read(65536)
            if not chunk:
                break
            total += len(chunk)
        if total > 2*1024*1024:
            result["error"] = "response_size_limit"
        result["size_download_bytes"] = total
    except socket.gaierror:
        result["error"] = "dns"
    except ssl.SSLError:
        result["error"] = "tls"
    except (TimeoutError,socket.timeout):
        result["error"] = "timeout"
    except (ConnectionError, OSError):
        result["error"] = "tcp"
    finally:
        if sock is not None:
            sock.close()
    result["duration_ms"] = round((time.monotonic()-start)*1000,2)
    result["timings_ms"]["total_ms"] = result["duration_ms"]
    result["diagnosis"] = diagnostic_for(result["status"],result["error"],result["duration_ms"])
    return result


def dns_check(host: str):
    if not host or len(host) > 253:
        raise ValueError("Invalid hostname")
    started = time.monotonic()
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        addresses = sorted({item[4][0] for item in infos})
        return {"host": host, "addresses": addresses,
                "duration_ms": round((time.monotonic() - started) * 1000, 2)}
    except OSError as exc:
        return {"host": host, "error": "dns", "error_code": getattr(exc, "errno", None)}


def tcp_check(host: str, port: int, timeout: float = 5):
    if not 1 <= int(port) <= 65535:
        raise ValueError("Invalid port")
    started = time.monotonic()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return {"host": host, "port": port, "open": True,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2)}
    except OSError as exc:
        return {"host": host, "port": port, "open": False,
                "error": "tcp", "error_code": getattr(exc, "errno", None)}


def tls_check(host: str, port: int = 443, timeout: float = 6):
    if not 1 <= int(port) <= 65535:
        raise ValueError("Invalid port")
    ctx = ssl.create_default_context()
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as wrapped:
                cert = wrapped.getpeercert()
                return {
                    "host": host, "port": port, "valid": True,
                    "tls_version": wrapped.version(), "cipher": wrapped.cipher()[0],
                    "subject": cert.get("subject"), "issuer": cert.get("issuer"),
                    "not_after": cert.get("notAfter"),
                    "handshake_ms": round((time.monotonic() - start) * 1000, 2)}
    except (ssl.SSLError, OSError) as exc:
        return {"host": host, "port": port, "valid": False,
                "error": "tls", "type": type(exc).__name__}


def analyze_har(path: str):
    obj = read_small_json(path, MAX_HAR)
    entries = obj.get("log", {}).get("entries", [])
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise ValueError("Invalid or oversized HAR entries")
    result = []
    for item in entries:
        try:
            request = item.get("request", {})
            response = item.get("response", {})
            url = safe_url(request.get("url", ""))
            method = request.get("method", "GET")
            duration = float(item.get("time", 0))
            status = int(response.get("status", 0))
            timings = item.get("timings", {})
            steps = {}
            for key in ("blocked", "dns", "connect", "ssl", "send", "wait", "receive"):
                value = timings.get(key, -1) if isinstance(timings, dict) else -1
                if isinstance(value, (int, float)) and value >= 0:
                    steps[key + "_ms"] = round(float(value), 2)
            safe_headers = safe_header_map(response.get("headers", []))
            result.append({
                "target": url, "method": method[:12], "status": status,
                "duration_ms": duration, "timings_ms": steps,
                "response_headers": safe_headers,
                "diagnosis": diagnostic_for(status, elapsed_ms=duration),
            })
        except (ValueError, TypeError, AttributeError):
            continue
    result.sort(key=lambda x: x["duration_ms"], reverse=True)
    failures = [x for x in result if x["status"] >= 400 or x["status"] == 0]
    return {"entries": len(result), "errors": len(failures),
            "slowest": result[:10], "failures": failures[:20]}


def correlate(probe_file: str, server_jsonl: str):
    probe_data = read_small_json(probe_file, MAX_LOG)
    trace_id = str(probe_data.get("request_id", ""))
    if not TRACE_ID.fullmatch(trace_id):
        raise ValueError("Probe requires safe request_id")
    path = Path(server_jsonl)
    if not path.is_file() or path.stat().st_size > MAX_LOG:
        raise ValueError("Server log missing or too large")
    matches = []
    with path.open(encoding="utf-8") as stream:
        for idx, line in enumerate(stream):
            if idx >= MAX_ENTRIES:
                break
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if not isinstance(item, dict):
                continue
            if str(item.get("request_id") or item.get("trace_id") or "") != trace_id:
                continue
            clean = {key: item[key] for key in ("request_id", "status", "upstream_status",
                                                  "request_time", "upstream_response_time",
                                                  "method", "route")
                     if key in item and isinstance(item[key], (str, int, float))}
            if "route" in clean:
                clean["route"] = str(clean["route"])[:120]
            matches.append(clean)
    return {"request_id": trace_id,
            "client": {"status": probe_data.get("status"),
                       "duration_ms": probe_data.get("duration_ms")},
            "server_matches": matches[:30],
            "hint": "Compare client total with reverse proxy request_time and upstream_response_time."}


def present(obj, json_mode: bool):
    if json_mode:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            print(f"{key}: {json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value}")
    else:
        print(obj)


def publish_to_hub(command,output):
    """Send a bounded, redacted diagnostic using the inherited Unix socket."""
    from n3xv5_core.ipc import PeripheralClient
    if command not in ("probe","dns","tcp","tls","har","correlate"):
        raise ValueError("Unsupported publication")
    if not os.environ.get("N3XV5_IPC_FD"):
        raise RuntimeError("The CLI must be launched by the authenticated HUB")
    data=dict(output)
    if command=="har":
        data["slowest"]=(data.get("slowest") or [])[:5]
        data["failures"]=(data.get("failures") or [])[:3]
    elif command=="correlate":
        data["server_matches"]=(data.get("server_matches") or [])[:8]
    # Keep payload well below the inherited socket's 8 KiB framing limit.
    # All raw HAR requests, cookies and bodies were already dropped in analysis.
    with_report={"command":command,"data":data}
    from n3xv5_core.ipc import encode
    while len(encode({"api":1,"id":"0"*16,"app_id":"nexus-nettrace",
                      "method":"nettrace.publish","params":with_report}))>7600:
        if command=="har" and data.get("slowest"):
            data["slowest"].pop()
        elif command=="har" and data.get("failures"):
            data["failures"].pop()
        elif command=="correlate" and data.get("server_matches"):
            data["server_matches"].pop()
        else:
            raise ValueError("Report exceeds IPC limit")
    client=PeripheralClient()
    try:
        result=client.request("nettrace.publish",with_report)
    finally:
        client.close()
    if result.get("error") or not result.get("result",{}).get("accepted"):
        raise PermissionError("HUB refused NetTrace publication")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="n3xv5-nettrace", description="N3XV5 NetTrace — VPS/Client HTTPS debug CLI")
    parser.add_argument("--json", action="store_true", help="Output redacted JSON")
    parser.add_argument("--hub-publish", action="store_true", help="Send diagnostic to HUB iFrame through local authenticated socket")
    parser.add_argument("--output", help="Save the redacted diagnostic JSON to a local file")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("probe", help="Measure one HTTP(S) request")
    p.add_argument("url")
    p.add_argument("--method", choices=("GET", "HEAD", "OPTIONS"), default="GET")
    p.add_argument("--timeout", type=float, default=15)
    p.add_argument("--engine", choices=("auto","curl","stdlib"), default="auto", help="stdlib is fully portable HTTP/1.1; curl supports richer HTTP/2 timing")
    p.add_argument("--origin", help="Optional CORS Origin header")
    p.add_argument("--request-id")
    p = sub.add_parser("hub", help="Query active N3XV5 HUB session over private IPC")
    p.add_argument("--connections", action="store_true", help="List permitted nonsecret connection descriptors")
    p = sub.add_parser("dns", help="Resolve host A/AAAA")
    p.add_argument("host")
    p = sub.add_parser("tcp", help="Check TCP connection")
    p.add_argument("host")
    p.add_argument("port", type=int)
    p = sub.add_parser("tls", help="Validate TLS certificate and negotiation")
    p.add_argument("host")
    p.add_argument("--port", type=int, default=443)
    p = sub.add_parser("har", help="Analyze Firefox/Chrome exported HAR (redacted)")
    p.add_argument("file")
    p = sub.add_parser("correlate", help="Match one probe JSON with VPS JSONL logs by request ID")
    p.add_argument("probe_json")
    p.add_argument("server_jsonl")
    args = parser.parse_args(argv)
    try:
        if args.command == "probe":
            selected=("curl" if shutil.which("curl") else "stdlib") if args.engine=="auto" else args.engine
            runner=probe if selected=="curl" else probe_stdlib
            output = runner(args.url, args.method, args.timeout,
                            request_id=args.request_id, origin=args.origin)
        elif args.command == "hub":
            from n3xv5_core.ipc import PeripheralClient
            if not __import__("os").environ.get("N3XV5_IPC_FD"):
                raise RuntimeError("Launch NetTrace from the authenticated HUB for IPC")
            client = PeripheralClient()
            try:
                method = "connections.list" if args.connections else "profile.info"
                output = client.request(method)
            finally:
                client.close()
        elif args.command == "dns":
            output = dns_check(args.host)
        elif args.command == "tcp":
            output = tcp_check(args.host, args.port)
        elif args.command == "tls":
            output = tls_check(args.host, args.port)
        elif args.command == "har":
            output = analyze_har(args.file)
        else:
            output = correlate(args.probe_json, args.server_jsonl)
        if args.output:
            out = Path(args.output).expanduser()
            if out.exists():
                raise ValueError("Refusing to overwrite an existing report")
            out.parent.mkdir(parents=True, exist_ok=True)
            fd = out.open("x", encoding="utf-8")
            with fd:
                if hasattr(__import__("os"), "fchmod"):
                    __import__("os").fchmod(fd.fileno(), 0o600)
                json.dump(output, fd, ensure_ascii=False, indent=2)
        if args.hub_publish:
            publish_to_hub(args.command,output)
        present(output, args.json)
        return 0 if not output.get("error") else 2
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print("NetTrace error: " + type(exc).__name__ + " (see input and options)", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
