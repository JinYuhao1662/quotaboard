"""API 冒烟测试：在随机端口起一个真实服务，用 urllib 打请求。"""

import json
import threading
import urllib.error
import urllib.request

import pytest

from quotaboard.server import QuotaServer
from quotaboard.storage import Storage, normalize_provider, validate_account, ValidationError

SAMPLE = {
    "owner": "我", "name": "主号", "provider": "Claude 20X", "account": "main@example.com", "password": "p@ss",
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
    ({**SAMPLE, "archived": "yes"}, "归档标记"),
    ({**SAMPLE, "archived": True, "archiveReason": "lost"}, "归档原因"),
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


@pytest.mark.parametrize("raw, expected", [
    ("Claude 20X", "Claude 20X"),
    ("  Claude   5x ", "Claude 5X"),
    ("ChatGPT-20x", "ChatGPT 20X"),
    ("Gemini20×", "Gemini 20X"),
    ("Claude Max 05X", "Claude Max 5X"),
    ("Kimi", "Kimi"),
    ("Codex", "Codex"),
    ("20X", "20X"),
])
def test_provider_tier_is_normalized(raw, expected):
    assert normalize_provider(raw) == expected


def test_provider_tier_normalized_on_save(base_url):
    status, a = call(f"{base_url}/api/accounts", "POST", {**SAMPLE, "provider": "claude  5x"})
    assert status == 201 and a["provider"] == "claude 5X"
    status, a = call(f"{base_url}/api/accounts/{a['id']}", "PUT", {"provider": "ChatGPT 20x"})
    assert status == 200 and a["provider"] == "ChatGPT 20X"


def test_archive_and_restore(base_url, monkeypatch):
    import quotaboard.storage as storage_mod

    status, a = call(f"{base_url}/api/accounts", "POST", SAMPLE)
    assert status == 201 and a["archived"] is False and a["archiveReason"] == "" and a["archivedAt"] is None

    monkeypatch.setattr(storage_mod, "now_iso", lambda: "2099-01-01T00:00:00Z")
    status, a = call(f"{base_url}/api/accounts/1", "PUT", {"archived": True, "archiveReason": "banned"})
    assert status == 200 and a["archived"] is True and a["archiveReason"] == "banned" and a["archivedAt"] == "2099-01-01T00:00:00Z"
    assert a["used"] == 35 and a["quotaUpdatedAt"] != "2099-01-01T00:00:00Z", "归档不动额度记录"

    monkeypatch.setattr(storage_mod, "now_iso", lambda: "2099-02-02T00:00:00Z")
    status, a = call(f"{base_url}/api/accounts/1", "PUT", {"archiveReason": "expired"})
    assert status == 200 and a["archiveReason"] == "expired" and a["archivedAt"] == "2099-01-01T00:00:00Z", "改原因不改归档时间"
    status, a = call(f"{base_url}/api/accounts/1", "PUT", {"notes": "申诉中"})
    assert status == 200 and a["archived"] is True and a["archiveReason"] == "expired", "编辑其它字段不影响归档状态"

    status, a = call(f"{base_url}/api/accounts/1", "PUT", {"archived": False})
    assert status == 200 and a["archived"] is False and a["archiveReason"] == "" and a["archivedAt"] is None

    status, a = call(f"{base_url}/api/accounts/1", "PUT", {"archived": True})
    assert status == 200 and a["archiveReason"] == "other" and a["archivedAt"] == "2099-02-02T00:00:00Z", "没给原因按其他；重新归档重新计时"

    status, listing = call(f"{base_url}/api/accounts")
    assert status == 200 and [x["archived"] for x in listing["accounts"]] == [True], "归档的账号仍在列表里，由前端分栏"


V1_DOC = {
    "version": 1, "nextId": 6,
    "accounts": [
        {"id": 1, "name": "主号", "provider": "Claude", "account": "a@example.com", "password": "p1", "used": 10},
        {"id": 2, "name": "备用", "provider": "ChatGPT", "account": "b@example.com", "password": "p2", "used": 20},
        {"id": 3, "name": "已写档位", "provider": "Claude 5x", "account": "c@example.com", "password": "p3", "used": 30},
        {"id": 5, "name": "其它", "provider": " Kimi ", "account": "d@example.com", "password": "p4", "used": 40},
    ],
}


def test_v1_file_is_upgraded_with_backup(tmp_path):
    path = tmp_path / "accounts.json"
    original = json.dumps(V1_DOC, ensure_ascii=False, indent=2)
    path.write_text(original, "utf-8")

    storage = Storage(path)
    doc = json.loads(path.read_text("utf-8"))
    assert doc["version"] == 2 and doc["nextId"] == 6
    assert [a["provider"] for a in doc["accounts"]] == ["Claude 20X", "ChatGPT 20X", "Claude 5X", "Kimi 20X"], "存量账号补 20X，已写档位的保留"
    assert all(a["archived"] is False and a["archiveReason"] == "" and a["archivedAt"] is None for a in doc["accounts"])
    assert [(a["id"], a["name"], a["password"], a["used"]) for a in doc["accounts"]] == [(a["id"], a["name"], a["password"], a["used"]) for a in V1_DOC["accounts"]]
    assert (tmp_path / "accounts.json.v1.bak").read_text("utf-8") == original, "升级前的文件原样备份"

    # 再开一次不重复升级、不覆盖备份
    (tmp_path / "accounts.json.v1.bak").write_text("keep", "utf-8")
    before = path.read_text("utf-8")
    assert [a["provider"] for a in Storage(path).list()] == [a["provider"] for a in storage.list()]
    assert path.read_text("utf-8") == before and (tmp_path / "accounts.json.v1.bak").read_text("utf-8") == "keep"


def test_old_file_swapped_in_while_running_is_upgraded_on_read(tmp_path):
    path = tmp_path / "accounts.json"
    storage = Storage(path)
    legacy = {k: v for k, v in V1_DOC.items() if k != "version"}   # 最早的文件没有 version
    path.write_text(json.dumps(legacy, ensure_ascii=False), "utf-8")

    assert [a["provider"] for a in storage.list()] == ["Claude 20X", "ChatGPT 20X", "Claude 5X", "Kimi 20X"]
    storage.update(1, {"used": 50})
    doc = json.loads(path.read_text("utf-8"))
    assert doc["version"] == 2 and doc["accounts"][1]["provider"] == "ChatGPT 20X", "下一次写入时落盘"


def test_broken_file_does_not_block_startup(tmp_path):
    path = tmp_path / "accounts.json"
    path.write_text("{not json", "utf-8")
    storage = Storage(path)
    assert path.read_text("utf-8") == "{not json" and not (tmp_path / "accounts.json.v1.bak").exists()
    with pytest.raises(RuntimeError, match="不是合法 JSON"):
        storage.list()


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
