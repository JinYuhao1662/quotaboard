"""访问口令与会话：PBKDF2 口令哈希、内存会话、连续失败计数与自锁（LOCKDOWN）。"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

log = logging.getLogger("quotaboard.auth")

PBKDF2_ITERATIONS = 600_000
COOKIE_NAME = "qb_session"


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> dict:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return {"algo": "pbkdf2_sha256", "iterations": iterations, "salt": salt.hex(), "hash": digest.hex()}


def verify_password(password: str, record: dict) -> bool:
    try:
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(record["salt"]), int(record["iterations"]))
        return hmac.compare_digest(digest.hex(), str(record["hash"]))
    except (KeyError, TypeError, ValueError):
        return False


def load_password_record(auth_file: Path) -> dict | None:
    try:
        rec = json.loads(Path(auth_file).read_text("utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(rec, dict) or rec.get("algo") != "pbkdf2_sha256":
        raise RuntimeError(f"口令文件格式不对：{auth_file}")
    return rec


def save_password_record(auth_file: Path, record: dict) -> None:
    auth_file = Path(auth_file)
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = auth_file.with_name(auth_file.name + ".tmp")
    tmp.write_text(json.dumps(record, indent=2) + "\n", "utf-8")
    tmp.replace(auth_file)


def read_lockdown(lockdown_file: Path) -> dict | None:
    """有锁定文件就返回其内容（解析失败也算锁定），没有返回 None。"""
    try:
        return json.loads(Path(lockdown_file).read_text("utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError):
        return {"time": "?", "ip": "?", "failures": "?"}


class Auth:
    """单口令、多会话。连续失败达到 max_failures 次 → 写锁定文件、清空会话、回调 on_lockdown（由服务端停止进程）。"""

    def __init__(
        self,
        record: dict,
        lockdown_file: Path,
        *,
        max_failures: int = 5,
        session_hours: float = 24,
        fail_delay: float = 1.0,
        on_lockdown: Callable[[], None] | None = None,
    ):
        self.record = record
        self.lockdown_file = Path(lockdown_file)
        self.max_failures = max(1, int(max_failures))
        self.session_seconds = float(session_hours) * 3600
        self.fail_delay = fail_delay
        self.on_lockdown = on_lockdown
        self.failures = 0
        self.locked = False
        self.sessions: dict[str, dict] = {}
        self._lock = threading.Lock()

    # ---- 登录 / 会话 ----
    def login(self, password: str, ip: str) -> tuple[str | None, int]:
        """返回 (会话令牌或 None, 剩余可尝试次数)。"""
        with self._lock:
            if self.locked:
                return None, 0
            if verify_password(password, self.record):
                self.failures = 0
                token = secrets.token_urlsafe(32)
                now = time.time()
                self.sessions[token] = {"created": now, "seen": now, "ip": ip}
                log.info("登录成功：%s", ip)
                return token, self.max_failures
            self.failures += 1
            remaining = self.max_failures - self.failures
            log.warning("口令错误（来源 %s），连续失败 %d/%d", ip, self.failures, self.max_failures)
            if remaining <= 0:
                self._lockdown(ip)
        if self.fail_delay:
            time.sleep(self.fail_delay)  # 拖慢暴力尝试；放在锁外，不阻塞其它请求
        return None, max(0, remaining)

    def check(self, token: str | None) -> bool:
        if not token:
            return False
        with self._lock:
            s = self.sessions.get(token)
            if not s:
                return False
            now = time.time()
            if now - s["seen"] > self.session_seconds:
                del self.sessions[token]
                return False
            s["seen"] = now
            return True

    def logout(self, token: str | None) -> None:
        if token:
            with self._lock:
                self.sessions.pop(token, None)

    # ---- 自锁 ----
    def _lockdown(self, ip: str) -> None:
        self.locked = True
        self.sessions.clear()
        info = {
            "time": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "ip": ip,
            "failures": self.failures,
        }
        try:
            self.lockdown_file.parent.mkdir(parents=True, exist_ok=True)
            self.lockdown_file.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", "utf-8")
        except OSError:
            log.exception("写入锁定文件失败：%s", self.lockdown_file)
        log.critical(
            "连续 %d 次口令错误（最后来源 %s），服务已锁定并停止。处理：先 python -m quotaboard set-password 换口令，再 python -m quotaboard unlock 后重新启动。",
            self.failures, ip,
        )
        if self.on_lockdown:
            self.on_lockdown()
