"""JSON 文件存储：单文件、加锁、原子写入、字段校验。"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
REQUIRED_TEXT = ("name", "provider", "account", "password")
OPTIONAL_TEXT = ("owner", "notes", "mailPlatform", "recoveryEmail", "phone", "smsPlatform", "totp")
SHARED_OWNER_ALIASES = {"全部", "共享"}  # 用户标签留空 = 共享账号（所有人可见）；这两个词也按留空处理
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
LABELS = {
    "owner": "用户标签",
    "name": "用户名",
    "provider": "服务商",
    "account": "账号",
    "password": "密码",
}


class ValidationError(ValueError):
    """请求数据不合法（返回 400）。"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_account(data: Any, *, partial: bool = False) -> dict:
    """校验并规范化账号字段。partial=True 时只处理请求里出现的字段（用于更新）。"""
    if not isinstance(data, dict):
        raise ValidationError("请求体必须是 JSON 对象")
    out: dict = {}

    for key in REQUIRED_TEXT:
        if key in data or not partial:
            val = str(data.get(key) or "").strip()
            if not val:
                raise ValidationError(f"{LABELS[key]}不能为空")
            out[key] = val

    if "resetDay" in data or not partial:
        try:
            day = int(data.get("resetDay"))
        except (TypeError, ValueError):
            raise ValidationError("重置时间（周几）必须是 1 到 7 的整数") from None
        if not 1 <= day <= 7:
            raise ValidationError("重置时间（周几）必须是 1 到 7 的整数")
        out["resetDay"] = day

    if "resetTime" in data or not partial:
        t = str(data.get("resetTime") or "").strip()
        if not TIME_RE.match(t):
            raise ValidationError("重置时间（几点）格式应为 HH:MM")
        out["resetTime"] = t

    if "subStart" in data or not partial:
        s = str(data.get("subStart") or "").strip()
        try:
            dt = datetime.fromisoformat(s)           # 接受 2026-09-21、2026-09-21T08:30、2026-09-21 08:30
        except ValueError:
            raise ValidationError("订阅开始时间格式应为 YYYY-MM-DDTHH:MM") from None
        if dt.tzinfo is not None:
            raise ValidationError("订阅开始时间不要带时区")
        out["subStart"] = dt.strftime("%Y-%m-%dT%H:%M")   # 统一带时分；只给日期的按 00:00

    if "used" in data or not partial:
        try:
            used = int(round(float(data.get("used"))))
        except (TypeError, ValueError):
            raise ValidationError("已用额度必须是 0 到 100 的数字") from None
        if not 0 <= used <= 100:
            raise ValidationError("已用额度必须是 0 到 100 的数字")
        out["used"] = used

    for key in OPTIONAL_TEXT:
        if key in data or not partial:
            out[key] = str(data.get(key) or "").strip()
    if out.get("owner") in SHARED_OWNER_ALIASES:
        out["owner"] = ""

    return out


class Storage:
    """所有账号存在一个 JSON 文件里：{"version", "nextId", "accounts": [...]}。"""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"version": SCHEMA_VERSION, "nextId": 1, "accounts": []})

    # ---------- 文件读写 ----------
    def _read(self) -> dict:
        try:
            with self.path.open("r", encoding="utf-8") as f:
                doc = json.load(f)
        except FileNotFoundError:
            doc = {}
        except json.JSONDecodeError as e:
            raise RuntimeError(f"数据文件 {self.path} 不是合法 JSON：{e}") from e
        if not isinstance(doc, dict):
            raise RuntimeError(f"数据文件 {self.path} 顶层必须是对象")
        doc.setdefault("version", SCHEMA_VERSION)
        doc.setdefault("accounts", [])
        doc.setdefault("nextId", max([int(a.get("id", 0)) for a in doc["accounts"]] + [0]) + 1)
        return doc

    def _write(self, doc: dict) -> None:
        tmp = self.path.with_name(self.path.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, self.path)

    # ---------- 对外接口 ----------
    def list(self) -> list[dict]:
        with self._lock:
            return self._read()["accounts"]

    def get(self, id_: int) -> dict | None:
        return next((a for a in self.list() if a.get("id") == id_), None)

    def create(self, data: Any) -> dict:
        fields = validate_account(data)
        with self._lock:
            doc = self._read()
            ts = now_iso()
            acc = {"id": doc["nextId"], **fields, "quotaUpdatedAt": ts, "createdAt": ts, "updatedAt": ts}
            doc["nextId"] += 1
            doc["accounts"].append(acc)
            self._write(doc)
            return acc

    def update(self, id_: int, data: Any) -> dict | None:
        fields = validate_account(data, partial=True)
        with self._lock:
            doc = self._read()
            acc = next((a for a in doc["accounts"] if a.get("id") == id_), None)
            if acc is None:
                return None
            ts = now_iso()
            acc.update(fields)
            if "used" in fields:  # 只要提交了已用额度，就视为重新记录了一次（前端只在改动或确认重置时提交）
                acc["quotaUpdatedAt"] = ts
            acc["updatedAt"] = ts
            self._write(doc)
            return acc

    def delete(self, id_: int) -> bool:
        with self._lock:
            doc = self._read()
            before = len(doc["accounts"])
            doc["accounts"] = [a for a in doc["accounts"] if a.get("id") != id_]
            if len(doc["accounts"]) == before:
                return False
            self._write(doc)
            return True

    def mtime(self) -> float | None:
        try:
            return self.path.stat().st_mtime
        except OSError:
            return None
