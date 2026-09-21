# Coding Plan 额度看板（quotaboard）

多个 Coding Plan 账号（Claude / ChatGPT / …）的已用额度、每周重置、订阅到期一览。
后端是 Python 标准库 HTTP 服务（零第三方依赖），前端是原生 JS 单页，数据明文存在本地 JSON 文件里；登录用访问口令，连续输错自动锁定停服。

## 本地运行

```powershell
uv sync                                        # 创建 .venv（无运行时依赖，只装 dev 组的 pytest）
uv run python -m quotaboard --host 127.0.0.1 --open   # 只本机访问、免登录、自动打开浏览器
uv run python -m quotaboard set-password       # 设置访问口令（交互输入两次，至少 8 位）
uv run python -m quotaboard                    # 0.0.0.0:8765，必须已设口令（或带 --client-ca / --no-auth）
uv run pytest -q                               # 测试
```

`--host 127.0.0.1` 且没设口令时免登录；监听其它地址而没有任何身份验证时拒绝启动，除非明确加 `--no-auth`。

### 参数（也可用同名环境变量 `QUOTABOARD_*`）

| 参数 | 默认 | 说明 |
|---|---|---|
| `--host` / `--port` | `0.0.0.0` / `8765` | 监听地址与端口 |
| `--data` | `data/accounts.json` | 数据文件（明文 JSON）；口令文件、锁定文件放在同一目录 |
| `--auth-file` | `<数据目录>/auth.json` | 口令哈希文件 |
| `--no-auth` | 关 | 不要口令 |
| `--max-failures` | `5` | 连续错口令多少次后锁定并停止服务 |
| `--session-hours` | `24` | 登录会话闲置多久失效 |
| `--cert` / `--key` | 无 | 服务端证书与私钥（PEM），给了就走 HTTPS |
| `--client-ca` | 无 | 要求客户端证书（mTLS），公网部署用 |
| `--secure-cookies` / `--trust-proxy` | 关 | 放在 HTTPS 反向代理后面时用 |
| `--log-file` | 无 | 日志文件，自动轮转 |
| `--open` | 关 | 启动后打开浏览器 |

子命令：`serve`（默认，可省略）、`set-password`（也接受管道输入）、`unlock`、`health`。

## 每个人自己的地址

`http://<主机>:<端口>/?user=<用户标签>` 只显示该用户的账号（含共享账号），例如 `http://192.168.50.201:38471/?user=我`；`?provider=Claude` 同理。
切换筛选时地址栏会自动同步，直接收藏即可；未登录打开会先去登录，登录后跳回原地址。排序、视图和上次的筛选也会记在浏览器里。

## 访问口令与自锁

- 口令用 PBKDF2-SHA256（60 万次迭代、随机盐）哈希后存在 `data/auth.json`，也可用环境变量 `QUOTABOARD_PASSWORD` 在启动时提供。
- 登录成功后发放 `HttpOnly; SameSite=Strict` 的会话 Cookie，会话只在内存里，闲置 24 小时失效，重启服务即全部失效。
- 每次口令错误延迟 1 秒；连续错 `--max-failures` 次（默认 5）就写入 `data/LOCKDOWN.json`、清空会话并停止进程（退出码 3）。锁定状态下服务拒绝启动，开机自启任务也拉不起来，必须人工处理：

  ```powershell
  uv run python -m quotaboard set-password     # 先换口令
  uv run python -m quotaboard unlock           # 再解除锁定，然后重新启动
  ```

- 代价：知道地址的人可以故意输错让服务停掉（拒绝服务），但拿不到数据。
- 所有响应带 `Content-Security-Policy`、`X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、`Referrer-Policy: no-referrer`。

## 数据文件

`data/accounts.json`，结构：`{"version": 1, "nextId": N, "accounts": [ … ]}`。每个账号：

| 字段 | 必填 | 说明 |
|---|---|---|
| `owner` | 否 | 用户标签（这个号给谁用），账号区按它分组；留空或填「全部」= 共享账号，不归属任何人，筛选任何用户时都显示 |
| `name` | 是 | 用户名（显示名） |
| `provider` | 是 | 服务商，如 Claude、ChatGPT；前端按名字匹配色卡，未知名字从备用色卡顺序取色 |
| `account` / `password` | 是 | 登录账号 / 密码（明文） |
| `resetDay` / `resetTime` | 是 | 每周重置：周几（1 = 周一 … 7 = 周日）/ `HH:MM` |
| `subStart` | 是 | 订阅开始日期 `YYYY-MM-DD`，订阅一个月，到期日自动算；到期后即使有额度也不可用 |
| `used` | 是 | 已用额度 0 到 100 |
| `quotaUpdatedAt` | 自动 | 上次记录已用额度的时间；早于最近一次重置点时前端按「已重置」（0%）显示 |
| `notes` `mailPlatform` `recoveryEmail` `phone` `smsPlatform` `totp` | 否 | 备注、邮件接码平台、辅助邮箱、手机号、短信接码平台、2FA |

写入是「写临时文件再替换」的原子操作，多线程访问加锁。

## API（除 `/api/ping`、`/login`、`/logout` 外都要先登录，未登录返回 401）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/ping` | 存活探针，不带数据 |
| GET / POST | `/login` | 登录页 / 表单提交（`password` 字段），成功后 302 回首页并下发 Cookie |
| POST | `/logout` | 退出，清 Cookie |
| GET | `/api/accounts` | 全部账号 |
| POST | `/api/accounts` | 新增，返回 201 |
| PUT | `/api/accounts/{id}` | 局部更新（只改提交的字段）。提交了 `used` 就刷新 `quotaUpdatedAt` |
| DELETE | `/api/accounts/{id}` | 删除 |
| GET | `/api/health` | 数据文件路径、账号数、修改时间、是否启用口令 / TLS |

校验失败返回 400 `{"error": "…"}`。

## 部署（局域网主机 192.168.50.201）

```powershell
.\deploy\deploy.ps1                 # 部署到 j14729c (192.168.50.201) 的 C:\ps_kernel\quotaboard，端口 38471
.\deploy\deploy.ps1 -SkipPassword   # 之后更新代码，不改口令
```

`deploy.ps1` 做的事：ssh 探活 → 远端没有 uv 就把本机 `uv.exe` 传到 `C:\temp\bootstrap\` → 同步项目文件（不碰远端 `data/`）
→ 远端 `uv sync --frozen --no-dev` 建 `.venv`（无依赖，不需要出网）→ 随机生成 20 位访问口令，文件对文件传到远端交给 `set-password`（不出现在任何命令行），保存在本机 `data\access-password.txt`
→ 防火墙放行、注册计划任务 `quotaboard-boot`（SYSTEM、开机自启、崩溃 1 分钟后自动重启，日志 `data\server.log`）并启动 → 本机探活 `http://192.168.50.201:38471/api/ping`。

远端命令一律经 `powershell -EncodedCommand` 执行，不依赖远端默认 shell；`.ps1` 文件保存为带 BOM 的 UTF-8（Windows PowerShell 5.1 才能正确读中文）。

服务器上的常用命令（PowerShell）：

```powershell
Get-ScheduledTask quotaboard-boot | Select-Object State
Stop-ScheduledTask quotaboard-boot; Start-ScheduledTask quotaboard-boot
Get-Content C:\ps_kernel\quotaboard\data\server.log -Tail 50
cd C:\ps_kernel\quotaboard; .venv\Scripts\python.exe -m quotaboard set-password    # 改口令后重启任务
cd C:\ps_kernel\quotaboard; .venv\Scripts\python.exe -m quotaboard unlock          # 自锁后解除
```

### 公网部署（可选，未启用）

代码已支持 HTTPS + 客户端证书：`.\deploy\make-certs.ps1` 生成私有 CA / 服务端 / 客户端证书（`certs/`，不入库），再
`.\deploy\deploy.ps1 -SshHost 139.159.214.28 -RemoteIp 139.159.214.28 -Root C:/ps-quotaboard -Tls`。
之后要把 `certs\client.pfx` 导入每台要用的设备、`ca.crt` 装进受信任根，并在云控制台安全组放行端口。没有证书的连接在 TLS 握手阶段就被拒绝，口令只是第二道门。

## 目录

```
quotaboard/   服务端（server.py 路由与命令行，auth.py 口令/会话/自锁，storage.py 存储与校验）
static/       前端（index.html / app.js / style.css / login.html）
data/         数据、口令哈希、锁定文件、日志（不入库、不随部署覆盖）
deploy/       deploy.ps1 / remote-setup.ps1 / make-certs.ps1
tests/        pytest（tests/certs 是仅供测试的自签证书）
```

## 许可

MIT，见 LICENSE。
