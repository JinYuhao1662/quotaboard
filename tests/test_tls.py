"""HTTPS + 客户端证书（mTLS）：没有有效客户端证书的连接在握手阶段被拒绝。证书见 tests/certs/README.md。"""

import json
import ssl
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from quotaboard.server import QuotaServer, main
from quotaboard.storage import Storage

CERTS = Path(__file__).parent / "certs"


def client_ctx(cert: str | None = "client"):
    ctx = ssl.create_default_context(cafile=str(CERTS / "ca.crt"))
    if cert:
        ctx.load_cert_chain(str(CERTS / f"{cert}.crt"), str(CERTS / f"{cert}.key"))
    return ctx


@pytest.fixture
def tls_server(tmp_path):
    sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    sctx.minimum_version = ssl.TLSVersion.TLSv1_2
    sctx.load_cert_chain(str(CERTS / "server.crt"), str(CERTS / "server.key"))
    sctx.verify_mode = ssl.CERT_REQUIRED
    sctx.load_verify_locations(cafile=str(CERTS / "ca.crt"))
    server = QuotaServer(("127.0.0.1", 0), Storage(tmp_path / "accounts.json"), None, ssl_context=sctx)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def ping_url(server):
    return f"https://127.0.0.1:{server.server_address[1]}/api/ping"


def test_valid_client_cert_is_accepted(tls_server):
    with urllib.request.urlopen(ping_url(tls_server), context=client_ctx("client"), timeout=5) as r:
        body = json.loads(r.read())
    assert r.status == 200 and body["ok"] is True and body["tls"] is True and body["clientCert"] == "quotaboard-test-client"


def test_missing_client_cert_is_rejected_and_server_survives(tls_server):
    with pytest.raises((urllib.error.URLError, ssl.SSLError, ConnectionError, OSError)):
        urllib.request.urlopen(ping_url(tls_server), context=client_ctx(None), timeout=5)
    with urllib.request.urlopen(ping_url(tls_server), context=client_ctx("client"), timeout=5) as r:
        assert r.status == 200, "被拒的握手不能影响后续正常连接"


def test_cert_from_other_ca_is_rejected(tls_server):
    with pytest.raises((urllib.error.URLError, ssl.SSLError, ConnectionError, OSError)):
        urllib.request.urlopen(ping_url(tls_server), context=client_ctx("rogue-client"), timeout=5)


def test_health_command_with_client_cert(tls_server, capsys):
    code = main(["health", "--url", ping_url(tls_server), "--ca", str(CERTS / "ca.crt"),
                 "--cert", str(CERTS / "client.crt"), "--key", str(CERTS / "client.key")])
    assert code == 0 and '"ok": true' in capsys.readouterr().out
    code = main(["health", "--url", ping_url(tls_server), "--ca", str(CERTS / "ca.crt")])
    assert code == 1, "没带客户端证书应探活失败"


def test_cli_allows_public_bind_with_client_ca_and_no_password(tmp_path):
    """--client-ca 时不设口令也允许对外监听：身份由证书保证。用 --port 0 只验证启动逻辑，随即因无事可做退出。"""
    import quotaboard.server as srv

    started = {}

    class FakeServer:
        lockdown_triggered = False

        def __init__(self, addr, storage, auth, **kw):
            started.update(addr=addr, auth=auth, ssl=kw.get("ssl_context"))

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            pass

    original = srv.QuotaServer
    srv.QuotaServer = FakeServer
    try:
        code = main(["serve", "--host", "0.0.0.0", "--port", "0", "--data", str(tmp_path / "a.json"),
                     "--cert", str(CERTS / "server.crt"), "--key", str(CERTS / "server.key"), "--client-ca", str(CERTS / "ca.crt")])
    finally:
        srv.QuotaServer = original
    assert code == 0 and started["auth"] is None and started["ssl"].verify_mode == ssl.CERT_REQUIRED
