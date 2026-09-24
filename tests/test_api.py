"""API 冒烟测试：在随机端口起一个真实服务，用 urllib 打请求。"""

import json
import threading
import urllib.error
import urllib.request

import pytest

from quotaboard.server import QuotaServer
from quotaboard.storage import Storage, validate_account, ValidationError

SAMPLE = {
    "owner": "我", "name": "主号", "provider": "Claude", "account": "main@example.com", "password": "p@ss",
    "resetDay": 3, "resetTime": "08:00", "subStart": "2026-09-09", "used": 35,
    "notes": "备注", "mailPlatform": "mail.tm", "recoveryEmail": "backup@example.com", "phone": "", "smsPlatform": "", "totp": "",
}


@pytest.fixture
def base_url(tmp_path):
    server = QuotaServer(("127.0.0.1", 0), Storage(tmp_path / "accounts.json"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def call(url, method="GET", body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, (json.loads(raw) if raw else None)


def test_crud_roundtrip(base_url):
    status, created = call(f"{base_url}/api/accounts", "POST", SAMPLE)
    assert status == 201 and created["id"] == 1 and created["quotaUpdatedAt"].endswith("Z")
    assert created["recoveryEmail"] == "backup@example.com"

    status, listing = call(f"{base_url}/api/accounts")
    assert status == 200 and [a["name"] for a in listing["accounts"]] == ["主号"]

    status, updated = call(f"{base_url}/api/accounts/1", "PUT", {"name": "主号-改", "notes": ""})
    assert status == 200 and updated["name"] == "主号-改" and updated["used"] == 35
    assert updated["quotaUpdatedAt"] == created["quotaUpdatedAt"], "未提交 used 时不应刷新额度记录时间"

    status, _ = call(f"{base_url}/api/accounts/1", "DELETE")
    assert status == 200
    status, _ = call(f"{base_url}/api/accounts/1")
    assert status == 404


def test_used_update_touches_quota_timestamp(base_url, monkeypatch):
    call(f"{base_url}/api/accounts", "POST", SAMPLE)
    import quotaboard.storage as storage_mod

    monkeypatch.setattr(storage_mod, "now_iso", lambda: "2099-01-01T00:00:00Z")
    status, updated = call(f"{base_url}/api/accounts/1", "PUT", {"used": 0})
    assert status == 200 and updated["used"] == 0 and updated["quotaUpdatedAt"] == "2099-01-01T00:00:00Z"


@pytest.mark.parametrize("bad, message", [
    ({**SAMPLE, "name": " "}, "用户名不能为空"),
    ({**SAMPLE, "resetDay": 8}, "重置时间（周几）"),
    ({**SAMPLE, "resetTime": "25:00"}, "HH:MM"),
    ({**SAMPLE, "subStart": "2026/09/09"}, "YYYY-MM-DDTHH:MM"),
    ({**SAMPLE, "subStart": "2026-09-09T08:30+08:00"}, "时区"),
    ({**SAMPLE, "used": 101}, "已用额度"),
])
def test_validation_errors(base_url, bad, message):
    status, body = call(f"{base_url}/api/accounts", "POST", bad)
    assert status == 400 and message in body["error"]


def test_owner_optional_and_shared_aliases(base_url):
    status, shared = call(f"{base_url}/api/accounts", "POST", {**SAMPLE, "owner": ""})
    assert status == 201 and shared["owner"] == "", "留空 = 共享账号"
    status, aliased = call(f"{base_url}/api/accounts", "POST", {**SAMPLE, "owner": "全部"})
    assert status == 201 and aliased["owner"] == "", "「全部」按共享处理"
    status, named = call(f"{base_url}/api/accounts", "POST", {**SAMPLE, "owner": " 我 "})
    assert status == 201 and named["owner"] == "我"


def test_sub_start_keeps_time_of_day(base_url):
    status, a = call(f"{base_url}/api/accounts", "POST", {**SAMPLE, "subStart": "2026-09-09T08:30"})
    assert status == 201 and a["subStart"] == "2026-09-09T08:30"
    status, b = call(f"{base_url}/api/accounts", "POST", {**SAMPLE, "subStart": "2026-09-09"})
    assert status == 201 and b["subStart"] == "2026-09-09T00:00", "只给日期按 00:00 补齐"
    status, c = call(f"{base_url}/api/accounts", "POST", {**SAMPLE, "subStart": "2026-09-09 21:05:30"})
    assert status == 201 and c["subStart"] == "2026-09-09T21:05", "秒被舍掉"


def test_validate_partial_only_touches_given_fields():
    assert validate_account({"used": "42.4"}, partial=True) == {"used": 42}
    with pytest.raises(ValidationError):
        validate_account({"resetDay": "x"}, partial=True)


def test_static_and_health(base_url):
    status, health = call(f"{base_url}/api/health")
    assert status == 200 and health["ok"] is True and health["count"] == 0

    with urllib.request.urlopen(f"{base_url}/", timeout=5) as r:
        assert r.status == 200 and "text/html" in r.headers["Content-Type"]
        assert "额度看板" in r.read().decode("utf-8")

    with urllib.request.urlopen(f"{base_url}/static/app.js", timeout=5) as r:
        assert "javascript" in r.headers["Content-Type"]

    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base_url}/static/../pyproject.toml", timeout=5)
    assert exc.value.code == 404
