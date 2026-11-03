"""Regression tests for privacy-first N3XV5 NetTrace diagnostics."""
from __future__ import annotations
import importlib.util
import json
import pathlib
import tempfile
from unittest.mock import patch
import pytest

MODULE_PATH=(pathlib.Path(__file__).resolve().parents[1]/"N3XV5"/"Applications"/"NexusNetTrace"/"nettrace.py")
spec=importlib.util.spec_from_file_location("n3xv5_nettrace",MODULE_PATH)
nettrace=importlib.util.module_from_spec(spec)
spec.loader.exec_module(nettrace)


def test_query_and_credentials_never_exported():
    value=nettrace.safe_url("https://example.test/login?token=private&password=secret&n=1#fragment")
    assert value=="https://example.test/login?token=[REDACTED]&password=[REDACTED]&n=[REDACTED]"
    for secret in ("private","secret","fragment"):
        assert secret not in value
    with pytest.raises(ValueError):
        nettrace.safe_url("https://alice:secret@example.test/")


def test_headers_do_not_leak_auth_or_cookies():
    h=nettrace.safe_header_map([
        {"name":"Authorization","value":"Bearer very-secret"},
        {"name":"Set-Cookie","value":"session=private"},
        {"name":"Content-Type","value":"text/html"},
        {"name":"Location","value":"https://example.test/?jwt=secret"},
        {"name":"X-Request-ID","value":"n3xv5-abc123"},
    ])
    assert h["content-type"]=="text/html"
    assert h["location"]=="https://example.test/?jwt=[REDACTED]"
    assert h["x-request-id"]=="n3xv5-abc123"
    assert "very-secret" not in repr(h)
    assert "session=private" not in repr(h)


def test_har_analyzes_browser_timings_without_sensitive_payload(tmp_path):
    data={"log":{"entries":[
        {"request":{"url":"https://sample.test/api?api_key=SECRET",
                    "method":"GET",
                    "headers":[{"name":"Cookie","value":"secret"}],
                    "postData":{"text":"VERY_PRIVATE"}},
         "response":{"status":502,"headers":[
             {"name":"Set-Cookie","value":"token=SECRET"},
             {"name":"X-Request-ID","value":"req-ab1"}]},
         "time":1245.6,"timings":{"dns":5,"connect":50,"ssl":110,"wait":1000,"receive":20}},
        {"request":{"url":"https://sample.test/ok","method":"GET"},
         "response":{"status":200,"headers":[]},"time":30,"timings":{}}
    ]}}
    path=tmp_path/"firefox.har"
    path.write_text(json.dumps(data))
    result=nettrace.analyze_har(str(path))
    assert result["entries"]==2 and result["errors"]==1
    assert result["slowest"][0]["status"]==502
    assert result["slowest"][0]["timings_ms"]["wait_ms"]==1000
    assert result["slowest"][0]["diagnosis"]["issue"]=="gateway_or_upstream"
    for private in ("SECRET","VERY_PRIVATE","Cookie"):
        assert private not in json.dumps(result)


def test_correlates_safe_client_vps_log(tmp_path):
    probe=tmp_path/"probe.json"
    logs=tmp_path/"vps.jsonl"
    probe.write_text(json.dumps({"request_id":"n3xv5-abcd","status":502,"duration_ms":1240}))
    logs.write_text("\n".join([
        json.dumps({"request_id":"wrong-id","status":200}),
        json.dumps({"request_id":"n3xv5-abcd","status":502,"upstream_status":502,
                    "request_time":"1.2","upstream_response_time":"1.18",
                    "authorization":"Bearer SECRET", "route":"/api/health"}),
        "bad-json",
    ]))
    report=nettrace.correlate(str(probe),str(logs))
    assert len(report["server_matches"])==1
    assert report["server_matches"][0]["upstream_status"]==502
    assert "SECRET" not in json.dumps(report)


def test_http_diagnoses_correct_failure():
    assert nettrace.diagnostic_for(401)["issue"]=="authentication_or_access"
    assert nettrace.diagnostic_for(502)["issue"]=="gateway_or_upstream"
    assert nettrace.diagnostic_for(200,elapsed_ms=2500)["issue"]=="slow_response"
    assert nettrace.diagnostic_for(None,"tls")["issue"]=="tls"


def test_probe_forbids_post_and_url_credentials():
    with pytest.raises(ValueError):
        nettrace.probe("https://example.org",method="POST")
    with pytest.raises(ValueError):
        nettrace.probe("https://user:password@example.org")


def test_dns_localhost():
    result=nettrace.dns_check("localhost")
    assert result["addresses"]


def test_cli_help_and_cli_bad_url(capsys):
    assert nettrace.main(["probe","file:///tmp/passwords"])==2
    captured=capsys.readouterr()
    assert "file:///tmp/passwords" not in captured.err
