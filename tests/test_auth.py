"""登录、会话、自锁的行为测试。"""

import http.cookies
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

from quotaboard.auth import Auth, hash_password, verify_password
from quotaboard.server import QuotaServer
from quotaboard.storage import Storage


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def request(url, method="GET", data=None, headers=None, form=None):
    """返回 (status, headers, body_bytes)，不跟随重定向。"""
    body = None
    hdrs = dict(headers or {})
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, method=method, headers=hdrs)
    try:
        with OPENER.open(req, timeout=5) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


@pytest.fixture
def srv(tmp_path):
    auth = Auth(hash_password("correct horse", iterations=1000), tmp_path / "LOCKDOWN.json", max_failures=3, session_hours=1, fail_delay=0)
    server = QuotaServer(("127.0.0.1", 0), Storage(tmp_path / "accounts.json"), auth)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.test_thread = thread
    server.tmp_path = tmp_path
    try:
        yield server
    finally:
        if thread.is_alive():
            server.shutdown()
        server.server_close()


def url(server, path):
    return f"http://127.0.0.1:{server.server_address[1]}{path}"


def cookie_of(headers):
    c = http.cookies.SimpleCookie()
    c.load(headers.get("Set-Cookie", ""))
    return c


def test_password_hashing_roundtrip():
    rec = hash_password("s3cret-pass", iterations=1000)
    assert verify_password("s3cret-pass", rec) and not verify_password("S3cret-pass", rec)
    assert not verify_password("x", {"algo": "pbkdf2_sha256"})


def test_unauthenticated_requests_are_denied(srv):
    status, headers, _ = request(url(srv, "/"))
    assert status == 302 and headers["Location"] == "/login"
    status, _, body = request(url(srv, "/api/accounts"))
    assert status == 401 and json.loads(body)["error"] == "未登录"
    status, _, _ = request(url(srv, "/api/accounts"), "POST", data={"name": "x"})
    assert status == 401
    status, headers, body = request(url(srv, "/login"))
    assert status == 200 and "text/html" in headers["Content-Type"] and "访问口令" in body.decode()


def test_login_logout_flow(srv):
    status, headers, body = request(url(srv, "/login"), "POST", form={"password": "wrong"})
    assert status == 401 and "还可尝试 2 次" in body.decode()

    status, headers, _ = request(url(srv, "/login"), "POST", form={"password": "correct horse"})
    assert status == 302 and headers["Location"] == "/"
    c = cookie_of(headers)["qb_session"]
    assert c["httponly"] and c["samesite"] == "Strict" and c["path"] == "/"
    cookie = {"Cookie": f"qb_session={c.value}"}

    status, _, body = request(url(srv, "/api/health"), headers=cookie)
    assert status == 200 and json.loads(body)["authEnabled"] is True
    status, _, _ = request(url(srv, "/api/accounts"), headers=cookie)
    assert status == 200
    status, headers, _ = request(url(srv, "/login"), headers=cookie)
    assert status == 302 and headers["Location"] == "/", "已登录访问 /login 应回首页"

    status, headers, _ = request(url(srv, "/logout"), "POST", headers=cookie)
    assert status == 302 and headers["Location"] == "/login"
    assert cookie_of(headers)["qb_session"]["max-age"] == "0"
    status, _, _ = request(url(srv, "/api/accounts"), headers=cookie)
    assert status == 401, "退出后旧会话失效"


def test_login_returns_to_requested_page(srv):
    status, headers, _ = request(url(srv, "/?user=%E6%88%91"))
    assert status == 302 and headers["Location"] == "/login?next=%2F%3Fuser%3D%25E6%2588%2591"
    status, _, body = request(url(srv, headers["Location"]))
    assert status == 200 and 'action="/login?next=%2F%3Fuser%3D%25E6%2588%2591"' in body.decode()
    status, headers, _ = request(url(srv, headers["Location"]), "POST", form={"password": "correct horse"})
    assert status == 302 and headers["Location"] == "/?user=%E6%88%91"
    # 站外地址不跟随
    status, headers, _ = request(url(srv, "/login?next=//evil.example/"), "POST", form={"password": "correct horse"})
    assert status == 302 and headers["Location"] == "/"


def test_lockdown_after_repeated_failures(srv):
    for i in range(2):
        status, _, _ = request(url(srv, "/login"), "POST", form={"password": f"bad{i}"})
        assert status == 401
    status, _, body = request(url(srv, "/login"), "POST", form={"password": "bad3"})
    assert status == 403 and "已锁定" in body.decode()

    lock = srv.tmp_path / "LOCKDOWN.json"
    assert lock.exists() and json.loads(lock.read_text("utf-8"))["failures"] == 3
    assert srv.lockdown_triggered
    srv.test_thread.join(timeout=5)
    assert not srv.test_thread.is_alive(), "触发自锁后 serve_forever 应退出"


def test_no_auth_server_is_open(tmp_path):
    server = QuotaServer(("127.0.0.1", 0), Storage(tmp_path / "accounts.json"), None)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        status, headers, _ = request(url(server, "/login"))
        assert status == 302 and headers["Location"] == "/"
        status, _, body = request(url(server, "/api/health"))
        assert status == 200 and json.loads(body)["authEnabled"] is False
    finally:
        server.shutdown()
        server.server_close()


def test_cli_refuses_public_bind_without_password(tmp_path, capsys):
    from quotaboard.server import main

    code = main(["serve", "--host", "0.0.0.0", "--port", "0", "--data", str(tmp_path / "a.json")])
    assert code == 2


def test_cli_refuses_to_start_when_locked(tmp_path):
    from quotaboard.server import main

    (tmp_path / "LOCKDOWN.json").write_text('{"time": "t", "ip": "1.2.3.4", "failures": 5}', "utf-8")
    code = main(["serve", "--host", "127.0.0.1", "--port", "0", "--data", str(tmp_path / "a.json")])
    assert code == 3
    assert main(["unlock", "--data", str(tmp_path / "a.json")]) == 0
    assert not (tmp_path / "LOCKDOWN.json").exists()


def test_cli_set_password_writes_hash(tmp_path):
    from quotaboard.server import main
    from quotaboard.auth import load_password_record

    data = tmp_path / "a.json"
    assert main(["set-password", "--data", str(data), "--password", "short"]) == 1
    assert main(["set-password", "--data", str(data), "--password", "long-enough-pw"]) == 0
    rec = load_password_record(tmp_path / "auth.json")
    assert rec["algo"] == "pbkdf2_sha256" and verify_password("long-enough-pw", rec)
