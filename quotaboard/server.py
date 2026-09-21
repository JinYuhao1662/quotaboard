"""Coding Plan 额度看板：标准库 HTTP 服务（静态页面 + JSON API + 访问口令），无第三方依赖。

    python -m quotaboard                       # 启动服务（默认 0.0.0.0:8765；非本机监听必须先设口令）
    python -m quotaboard set-password          # 设置访问口令（存 data/auth.json，PBKDF2 哈希）
    python -m quotaboard unlock                # 连续错口令触发自锁后，解除锁定
"""

from __future__ import annotations

import argparse
import getpass
import json
import logging
import mimetypes
import os
import ssl
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from .auth import COOKIE_NAME, Auth, hash_password, load_password_record, read_lockdown, save_password_record
from .storage import Storage, ValidationError

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
DEFAULT_DATA = ROOT / "data" / "accounts.json"
LOCKDOWN_EXIT_CODE = 3

log = logging.getLogger("quotaboard")
mimetypes.add_type("application/javascript", ".js")

CSP = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"


class QuotaServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        addr: tuple[str, int],
        storage: Storage,
        auth: Auth | None = None,
        *,
        static_dir: Path = STATIC_DIR,
        secure_cookies: bool = False,
        trust_proxy: bool = False,
        ssl_context: ssl.SSLContext | None = None,
    ):
        super().__init__(addr, Handler)
        self.storage = storage
        self.auth = auth
        self.static_dir = Path(static_dir)
        self.secure_cookies = secure_cookies or ssl_context is not None
        self.trust_proxy = trust_proxy
        self.ssl_context = ssl_context
        self.lockdown_triggered = False
        if auth is not None:
            auth.on_lockdown = self.trigger_lockdown

    # TLS 握手放到工作线程里做：不能在 accept 循环里握手，否则一个慢客户端就能卡住所有人
    def get_request(self):
        sock, addr = self.socket.accept()
        if self.ssl_context is not None:
            sock.settimeout(15)
            sock = self.ssl_context.wrap_socket(sock, server_side=True, do_handshake_on_connect=False)
        return sock, addr

    def process_request_thread(self, request, client_address):
        if self.ssl_context is not None:
            try:
                request.do_handshake()
                request.settimeout(None)
            except (ssl.SSLError, OSError) as e:
                log.warning("TLS 握手失败（%s）：%s", client_address[0], getattr(e, "reason", None) or e)
                self.shutdown_request(request)
                return
        super().process_request_thread(request, client_address)

    def trigger_lockdown(self) -> None:
        """自锁：在另一个线程里停掉 serve_forever（不能在请求线程里直接 shutdown）。"""
        self.lockdown_triggered = True
        threading.Thread(target=self.shutdown, name="quotaboard-lockdown", daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    server_version = "quotaboard/0.2"
    protocol_version = "HTTP/1.1"
    server: QuotaServer  # type: ignore[assignment]

    # ---------- 响应工具 ----------
    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CSP)

    def _send_bytes(self, status: int, body: bytes, ctype: str, cache: str = "no-store", extra: list[tuple[str, str]] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self._security_headers()
        for k, v in extra or []:
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload, extra: list[tuple[str, str]] | None = None) -> None:
        self._send_bytes(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", extra=extra)

    def _error(self, status: int, message: str) -> None:
        self._json(status, {"error": message})

    def _redirect(self, location: str, extra: list[tuple[str, str]] | None = None) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        for k, v in extra or []:
            self.send_header(k, v)
        self.end_headers()

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length > 0 else b""

    def _read_json(self):
        raw = self._read_body()
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValidationError("请求体不是合法 JSON") from None

    def _route(self) -> tuple[str, list[str]]:
        path = urlsplit(self.path).path
        return path, [p for p in path.split("/") if p]

    @staticmethod
    def _account_id(parts: list[str]) -> int | None:
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "accounts" and parts[2].isdigit():
            return int(parts[2])
        return None

    def _client_ip(self) -> str:
        if self.server.trust_proxy:
            fwd = self.headers.get("X-Forwarded-For")
            if fwd:
                return fwd.split(",")[0].strip()
        return self.client_address[0]

    def _peer_cn(self) -> str | None:
        """mTLS 下客户端证书的 CN（用于日志 / 健康信息），非 TLS 连接返回 None。"""
        getpeercert = getattr(self.connection, "getpeercert", None)
        if getpeercert is None:
            return None
        try:
            info = getpeercert() or {}
        except (ValueError, OSError):
            return None
        for rdn in info.get("subject", ()):
            for key, value in rdn:
                if key == "commonName":
                    return value
        return None

    # ---------- 认证 ----------
    def _session_token(self) -> str | None:
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        c = SimpleCookie()
        try:
            c.load(raw)
        except Exception:  # noqa: BLE001
            return None
        m = c.get(COOKIE_NAME)
        return m.value if m else None

    def _cookie(self, token: str, max_age: int) -> tuple[str, str]:
        parts = [f"{COOKIE_NAME}={token}", "Path=/", "HttpOnly", "SameSite=Strict", f"Max-Age={max_age}"]
        if self.server.secure_cookies:
            parts.append("Secure")
        return ("Set-Cookie", "; ".join(parts))

    def _authorized(self) -> bool:
        auth = self.server.auth
        return auth is None or auth.check(self._session_token())

    def _deny(self, path: str) -> None:
        if path.startswith("/api/"):
            self._error(HTTPStatus.UNAUTHORIZED, "未登录")
        else:  # 登录后跳回原地址（比如 /?user=xxx）
            self._redirect("/login" if self.path in ("/", "") else "/login?next=" + quote(self.path, safe=""))

    def _next_url(self) -> str:
        """登录页 / 登录提交里的 next 参数，只接受站内相对路径。"""
        n = (parse_qs(urlsplit(self.path).query).get("next") or [""])[0]
        return n if n.startswith("/") and not n.startswith("//") and "\\" not in n else "/"

    def _render_login(self, status: int, error: str = "", hint: str = "") -> None:
        page = (self.server.static_dir / "login.html").read_text("utf-8")
        nxt = self._next_url()
        action = "/login" + ("?next=" + quote(nxt, safe="") if nxt != "/" else "")
        page = page.replace("__ERROR__", _html_escape(error)).replace("__HINT__", _html_escape(hint)).replace("__ACTION__", _html_escape(action))
        self._send_bytes(status, page.encode("utf-8"), "text/html; charset=utf-8")

    def _serve_static(self, rel: str) -> None:
        base = self.server.static_dir.resolve()
        target = (base / rel).resolve()
        if (target != base and base not in target.parents) or not target.is_file():
            return self._error(HTTPStatus.NOT_FOUND, "Not found")
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self._send_bytes(HTTPStatus.OK, target.read_bytes(), ctype, cache="no-cache")

    # ---------- 路由 ----------
    def do_GET(self) -> None:
        path, parts = self._route()
        try:
            auth = self.server.auth
            if path == "/api/ping":  # 存活探针：登录前可用，不带任何数据
                return self._json(HTTPStatus.OK, {"ok": True, "tls": self.server.ssl_context is not None, "clientCert": self._peer_cn()})
            if path == "/login":
                if auth is None:
                    return self._redirect("/")
                if auth.locked:
                    return self._render_login(HTTPStatus.FORBIDDEN, "口令连续错误次数过多，服务已锁定并停止。")
                if self._authorized():
                    return self._redirect(self._next_url())
                return self._render_login(HTTPStatus.OK)
            if not self._authorized():
                return self._deny(path)

            if path in ("/", "/index.html"):
                return self._serve_static("index.html")
            if parts and parts[0] == "static":
                return self._serve_static("/".join(parts[1:]))
            if path == "/api/health":
                st = self.server.storage
                return self._json(HTTPStatus.OK, {
                    "ok": True, "dataPath": str(st.path), "count": len(st.list()), "mtime": st.mtime(),
                    "authEnabled": auth is not None, "tls": self.server.ssl_context is not None, "clientCert": self._peer_cn(),
                })
            if path == "/api/accounts":
                return self._json(HTTPStatus.OK, {"accounts": self.server.storage.list()})
            if (id_ := self._account_id(parts)) is not None:
                acc = self.server.storage.get(id_)
                return self._json(HTTPStatus.OK, acc) if acc else self._error(HTTPStatus.NOT_FOUND, "账号不存在")
            return self._error(HTTPStatus.NOT_FOUND, "Not found")
        except Exception as e:  # noqa: BLE001 - 任何异常都以 JSON 500 返回
            log.exception("GET %s failed", path)
            return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    do_HEAD = do_GET

    def do_POST(self) -> None:
        path, _ = self._route()
        try:
            auth = self.server.auth
            if path == "/login":
                if auth is None:
                    self._read_body()
                    return self._redirect("/")
                form = parse_qs(self._read_body().decode("utf-8", "replace"))
                password = (form.get("password") or [""])[0]
                who = self._client_ip() + (f" cert={cn}" if (cn := self._peer_cn()) else "")
                token, remaining = auth.login(password, who)
                if token:
                    return self._redirect(self._next_url(), extra=[self._cookie(token, int(auth.session_seconds))])
                if auth.locked:
                    return self._render_login(HTTPStatus.FORBIDDEN, "口令连续错误次数过多，服务已锁定并停止。")
                return self._render_login(HTTPStatus.UNAUTHORIZED, "口令不对。", f"还可尝试 {remaining} 次，之后自动锁定。")
            if path == "/logout":
                self._read_body()
                if auth is not None:
                    auth.logout(self._session_token())
                return self._redirect("/login" if auth is not None else "/", extra=[self._cookie("", 0)])
            if not self._authorized():
                return self._deny(path)

            if path == "/api/accounts":
                acc = self.server.storage.create(self._read_json())
                log.info("新增账号 #%s %s", acc["id"], acc["name"])
                return self._json(HTTPStatus.CREATED, acc)
            return self._error(HTTPStatus.NOT_FOUND, "Not found")
        except ValidationError as e:
            return self._error(HTTPStatus.BAD_REQUEST, str(e))
        except Exception as e:  # noqa: BLE001
            log.exception("POST %s failed", path)
            return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def do_PUT(self) -> None:
        path, parts = self._route()
        try:
            if not self._authorized():
                return self._deny(path)
            if (id_ := self._account_id(parts)) is not None:
                acc = self.server.storage.update(id_, self._read_json())
                if acc is None:
                    return self._error(HTTPStatus.NOT_FOUND, "账号不存在")
                log.info("更新账号 #%s %s", acc["id"], acc["name"])
                return self._json(HTTPStatus.OK, acc)
            return self._error(HTTPStatus.NOT_FOUND, "Not found")
        except ValidationError as e:
            return self._error(HTTPStatus.BAD_REQUEST, str(e))
        except Exception as e:  # noqa: BLE001
            log.exception("PUT %s failed", path)
            return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    do_PATCH = do_PUT

    def do_DELETE(self) -> None:
        path, parts = self._route()
        try:
            if not self._authorized():
                return self._deny(path)
            if (id_ := self._account_id(parts)) is not None:
                if self.server.storage.delete(id_):
                    log.info("删除账号 #%s", id_)
                    return self._json(HTTPStatus.OK, {"ok": True})
                return self._error(HTTPStatus.NOT_FOUND, "账号不存在")
            return self._error(HTTPStatus.NOT_FOUND, "Not found")
        except Exception as e:  # noqa: BLE001
            log.exception("DELETE %s failed", path)
            return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def log_message(self, fmt: str, *args) -> None:  # 访问日志降为 debug，避免刷屏
        log.debug("%s - %s", self.address_string(), fmt % args)


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---------- 命令行 ----------
def setup_logging(log_file: str | None) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台默认 GBK，统一成 UTF-8 输出中文日志
    except (AttributeError, ValueError):
        pass
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers)


def _is_loopback(host: str) -> bool:
    return host in ("127.0.0.1", "localhost", "::1")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quotaboard", description="Coding Plan 额度看板")
    sub = p.add_subparsers(dest="command")

    s = sub.add_parser("serve", help="启动服务（不写子命令时默认就是它）")
    s.add_argument("--host", default=os.environ.get("QUOTABOARD_HOST", "0.0.0.0"), help="监听地址，默认 0.0.0.0；非本机监听必须设口令或加 --no-auth")
    s.add_argument("--port", type=int, default=int(os.environ.get("QUOTABOARD_PORT", "8765")), help="端口，默认 8765")
    s.add_argument("--data", default=os.environ.get("QUOTABOARD_DATA", str(DEFAULT_DATA)), help="数据文件路径（明文 JSON）；口令文件与锁定文件放在同目录")
    s.add_argument("--auth-file", default=os.environ.get("QUOTABOARD_AUTH_FILE"), help="口令哈希文件，默认 <数据目录>/auth.json")
    s.add_argument("--no-auth", action="store_true", help="不要口令（只建议可信内网）")
    s.add_argument("--max-failures", type=int, default=int(os.environ.get("QUOTABOARD_MAX_FAILURES", "5")), help="连续错口令多少次后锁定并停止服务，默认 5")
    s.add_argument("--session-hours", type=float, default=float(os.environ.get("QUOTABOARD_SESSION_HOURS", "24")), help="登录会话闲置多少小时失效，默认 24")
    s.add_argument("--cert", help="TLS 证书（PEM）；给了就走 HTTPS")
    s.add_argument("--key", help="TLS 私钥（PEM）")
    s.add_argument("--client-ca", help="要求客户端证书（mTLS）：签发客户端证书的 CA（PEM）。没有有效证书的连接在握手阶段就被拒绝")
    s.add_argument("--secure-cookies", action="store_true", help="Cookie 加 Secure（放在 HTTPS 反向代理后面时用；--cert 时自动开启）")
    s.add_argument("--trust-proxy", action="store_true", help="信任 X-Forwarded-For 作为来源 IP（仅在反向代理后面用）")
    s.add_argument("--log-file", default=os.environ.get("QUOTABOARD_LOG"), help="日志文件（可选，自动轮转）")
    s.add_argument("--open", action="store_true", help="启动后自动打开浏览器")

    sp = sub.add_parser("set-password", help="设置访问口令（交互输入，或 --password / 环境变量 QUOTABOARD_PASSWORD）")
    sp.add_argument("--data", default=os.environ.get("QUOTABOARD_DATA", str(DEFAULT_DATA)))
    sp.add_argument("--auth-file", default=os.environ.get("QUOTABOARD_AUTH_FILE"))
    sp.add_argument("--password", help="直接给口令（会留在 shell 历史里，不推荐）")

    un = sub.add_parser("unlock", help="解除自锁（删除 LOCKDOWN.json）；请先换口令")
    un.add_argument("--data", default=os.environ.get("QUOTABOARD_DATA", str(DEFAULT_DATA)))

    h = sub.add_parser("health", help="探活：请求 /api/ping（支持 HTTPS 与客户端证书）")
    h.add_argument("--url", default="http://127.0.0.1:8765/api/ping")
    h.add_argument("--ca", help="校验服务端证书用的 CA（PEM）")
    h.add_argument("--cert", help="客户端证书（PEM）")
    h.add_argument("--key", help="客户端私钥（PEM）")
    h.add_argument("--insecure", action="store_true", help="不校验服务端证书")
    return p


def _paths(args) -> tuple[Path, Path, Path]:
    data_path = Path(args.data)
    auth_file = Path(args.auth_file) if getattr(args, "auth_file", None) else data_path.parent / "auth.json"
    return data_path, auth_file, data_path.parent / "LOCKDOWN.json"


def cmd_set_password(args) -> int:
    _, auth_file, _ = _paths(args)
    pw = args.password or os.environ.get("QUOTABOARD_PASSWORD") or ""
    if not pw and not sys.stdin.isatty():
        pw = sys.stdin.readline().rstrip("\r\n")  # 管道 / ssh 传入：echo 口令 | python -m quotaboard set-password
    if not pw:
        pw = getpass.getpass("新口令：")
        if pw != getpass.getpass("再输一次："):
            print("两次输入不一致", file=sys.stderr)
            return 1
    if len(pw) < 8:
        print("口令至少 8 位", file=sys.stderr)
        return 1
    save_password_record(auth_file, hash_password(pw))
    print(f"口令已保存到 {auth_file}（PBKDF2-SHA256 哈希）。正在运行的服务需要重启才会用新口令。")
    return 0


def cmd_unlock(args) -> int:
    _, _, lockdown_file = _paths(args)
    info = read_lockdown(lockdown_file)
    if info is None:
        print("没有锁定，无需解除。")
        return 0
    lockdown_file.unlink()
    print(f"已解除锁定（此前于 {info.get('time')} 被 {info.get('ip')} 连续 {info.get('failures')} 次错口令触发）。如果还没换口令，先执行 set-password。")
    return 0


def cmd_health(args) -> int:
    import urllib.error
    import urllib.request

    ctx = None
    if args.url.lower().startswith("https"):
        ctx = ssl.create_default_context(cafile=args.ca) if args.ca else ssl.create_default_context()
        if args.insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        if args.cert:
            ctx.load_cert_chain(args.cert, args.key)
    try:
        with urllib.request.urlopen(args.url, timeout=8, context=ctx) as r:
            print(r.status, r.read().decode("utf-8", "replace"))
            return 0 if r.status == 200 else 1
    except urllib.error.HTTPError as e:
        print(e.code, e.read().decode("utf-8", "replace"))
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"ERROR {type(e).__name__}: {e}")
        return 1


def cmd_serve(args) -> int:
    setup_logging(args.log_file)
    data_path, auth_file, lockdown_file = _paths(args)

    info = read_lockdown(lockdown_file)
    if info is not None:
        log.error("服务处于锁定状态（%s 来自 %s 的连续 %s 次错口令）。先 set-password 换口令，再 unlock 解除后启动。", info.get("time"), info.get("ip"), info.get("failures"))
        return LOCKDOWN_EXIT_CODE

    auth: Auth | None = None
    if not args.no_auth:
        env_pw = os.environ.get("QUOTABOARD_PASSWORD")
        record = hash_password(env_pw) if env_pw else load_password_record(auth_file)
        if record is None:
            if _is_loopback(args.host):
                log.warning("未设置访问口令，仅本机监听 %s，跳过登录。对外开放前请先执行 set-password。", args.host)
            elif args.client_ca:
                log.info("未设置访问口令，由客户端证书（mTLS）完成身份验证")
            else:
                log.error("监听 %s 会暴露给网络，但还没有设置访问口令。先执行 python -m quotaboard set-password；确实不需要口令（可信内网）请加 --no-auth。", args.host)
                return 2
        else:
            auth = Auth(record, lockdown_file, max_failures=args.max_failures, session_hours=args.session_hours)
    elif args.client_ca:
        log.info("--no-auth：不用口令，由客户端证书（mTLS）完成身份验证")
    else:
        log.warning("--no-auth：没有登录保护，任何能连到 %s:%s 的人都能看到明文密码。", args.host, args.port)

    if bool(args.cert) != bool(args.key):
        log.error("--cert 和 --key 要一起给")
        return 2
    if args.client_ca and not args.cert:
        log.error("--client-ca 需要同时给 --cert / --key")
        return 2

    ctx = None
    if args.cert:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(args.cert, args.key)
        if args.client_ca:
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.load_verify_locations(cafile=args.client_ca)

    storage = Storage(data_path)
    server = QuotaServer((args.host, args.port), storage, auth, secure_cookies=args.secure_cookies, trust_proxy=args.trust_proxy, ssl_context=ctx)
    scheme = "https" if ctx else "http"

    shown_host = "127.0.0.1" if args.host in ("", "0.0.0.0") else args.host
    url = f"{scheme}://{shown_host}:{args.port}/"
    log.info("quotaboard 已启动：%s（监听 %s:%s，%s%s）数据文件：%s", url, args.host, args.port,
             "需要口令" if auth else "无口令", "，要求客户端证书" if args.client_ca else "", storage.path)
    if args.open:
        threading.Timer(0.5, webbrowser.open, (url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("收到中断，停止服务")
    finally:
        server.server_close()
    if server.lockdown_triggered:
        log.critical("服务因连续错口令自锁停止（退出码 %d）", LOCKDOWN_EXIT_CODE)
        return LOCKDOWN_EXIT_CODE
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0] not in ("serve", "set-password", "unlock", "health") and argv[0] not in ("-h", "--help")):
        argv.insert(0, "serve")
    args = build_parser().parse_args(argv)
    if args.command == "set-password":
        return cmd_set_password(args)
    if args.command == "unlock":
        return cmd_unlock(args)
    if args.command == "health":
        return cmd_health(args)
    return cmd_serve(args)


if __name__ == "__main__":
    raise SystemExit(main())
