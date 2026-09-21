<#
.SYNOPSIS
  一键部署。默认局域网主机（SSH 别名 j14729c = 192.168.50.201，根目录 C:\ps_kernel\quotaboard，端口 38471，HTTP + 口令登录，开机自启）。
  远端命令一律经 powershell -EncodedCommand 执行，不依赖远端默认 shell 是 cmd 还是 PowerShell；路径写正斜杠。
  步骤：ssh 探活 → 远端没有 uv 就上传本机 uv.exe → 同步项目文件（不碰远端 data/）→ 远端建 .venv
       → 随机生成访问口令，文件对文件传到远端交给 set-password（不出现在任何命令行）→ 注册计划任务并启动 → 本机探活。
.EXAMPLE
  .\deploy\deploy.ps1                                   # 局域网
  .\deploy\deploy.ps1 -SkipPassword                     # 更新代码，不改口令
  .\deploy\deploy.ps1 -SshHost 139.159.214.28 -RemoteIp 139.159.214.28 -Root C:/ps-quotaboard -Tls   # 公网：HTTPS + 客户端证书（先 make-certs.ps1）
#>
param(
  [string]$SshHost = "j14729c",
  [string]$RemoteIp = "192.168.50.201",
  [string]$Root = "C:/ps_kernel/quotaboard",
  [int]$Port = 38471,
  [switch]$Tls,
  [string]$CertsDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "certs"),
  [switch]$NoAuth,
  [switch]$SkipPassword
)
$ErrorActionPreference = "Stop"
$Local = Split-Path -Parent $PSScriptRoot
$Root = $Root -replace '\\', '/'
$RootWin = $Root -replace '/', '\'

function Invoke-Remote([string]$Script) {
  $b64 = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes("[Console]::OutputEncoding=[Text.Encoding]::UTF8; `$ProgressPreference='SilentlyContinue'; " + $Script))
  $out = ssh -o BatchMode=yes $SshHost "powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand $b64"
  if ($LASTEXITCODE -ne 0) { throw "远端命令失败（exit $LASTEXITCODE）：$Script`n$out" }
  $out
}
function Copy-Remote([string[]]$Paths, [string]$Dest) {
  scp -q -r $Paths "${SshHost}:$Dest"
  if ($LASTEXITCODE -ne 0) { throw "scp 失败：$($Paths -join ', ') -> $Dest" }
}

# ---- 0. 探活 ----
$hn = (Invoke-Remote "hostname") | Select-Object -Last 1
Write-Host "==> $SshHost ($RemoteIp) = $hn，根目录 $RootWin，端口 $Port，$(if ($Tls) { 'HTTPS + 客户端证书' } else { 'HTTP' })"

# ---- 1. 证书（仅 -Tls）----
if ($Tls) {
  foreach ($f in @("ca.crt", "server.crt", "server.key", "client.crt", "client.key")) {
    if (-not (Test-Path (Join-Path $CertsDir $f))) { throw "缺少 $CertsDir\$f，先运行 .\deploy\make-certs.ps1" }
  }
}

# ---- 2. uv ----
$hasUv = (Invoke-Remote "(Test-Path C:/temp/bootstrap/uv.exe) -or [bool](Get-Command uv -ErrorAction SilentlyContinue)") | Select-Object -Last 1
if ("$hasUv".Trim() -ne "True") {
  $localUv = (Get-Command uv).Source
  Write-Host "==> 远端没有 uv，上传本机 $localUv → C:/temp/bootstrap/uv.exe"
  Invoke-Remote "New-Item -ItemType Directory -Force C:/temp/bootstrap | Out-Null" | Out-Null
  Copy-Remote @($localUv) "C:/temp/bootstrap/uv.exe"
}

# ---- 3. 同步文件 ----
$stage = Join-Path $env:TEMP ("quotaboard-deploy-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force $stage | Out-Null
foreach ($item in @("pyproject.toml", "uv.lock", ".python-version", "README.md", "quotaboard", "static", "deploy")) {
  Copy-Item (Join-Path $Local $item) -Destination $stage -Recurse -Force
}
Get-ChildItem $stage -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
if ($Tls) {
  New-Item -ItemType Directory -Force (Join-Path $stage "certs") | Out-Null
  foreach ($f in @("ca.crt", "server.crt", "server.key")) { Copy-Item (Join-Path $CertsDir $f) (Join-Path $stage "certs") }   # 只传服务端需要的三件
}
Invoke-Remote "New-Item -ItemType Directory -Force $Root, $Root/data, C:/temp/bootstrap | Out-Null" | Out-Null
Write-Host "==> scp 项目文件 → ${SshHost}:$Root/"
Copy-Remote (Get-ChildItem $stage -Force | ForEach-Object { $_.FullName }) "$Root/"
Remove-Item $stage -Recurse -Force

# ---- 4. 远端建环境 ----
$setup = "powershell -NoProfile -ExecutionPolicy Bypass -File $Root/deploy/remote-setup.ps1 -Root $Root -Port $Port"
Invoke-Remote "$setup -Stage env"

# ---- 5. 口令：随机 20 位，写临时文件 scp 过去，远端从文件喂给 set-password 后删除 ----
$pwFile = Join-Path $Local "data\access-password.txt"
if (-not $NoAuth -and -not $SkipPassword) {
  $chars = (48..57) + (65..90) + (97..122)
  $password = -join ((1..20) | ForEach-Object { [char]($chars | Get-Random) })
  $tmp = Join-Path $env:TEMP ("quotaboard-pw-" + [guid]::NewGuid().ToString("N") + ".txt")
  [IO.File]::WriteAllText($tmp, $password + "`n", [Text.Encoding]::ASCII)
  Copy-Remote @($tmp) "C:/temp/bootstrap/quotaboard-pw.txt"
  Remove-Item $tmp -Force
  Invoke-Remote "Set-Location $Root; Get-Content C:/temp/bootstrap/quotaboard-pw.txt | .venv/Scripts/python.exe -m quotaboard set-password --data $Root/data/accounts.json; Remove-Item C:/temp/bootstrap/quotaboard-pw.txt -Force" | Out-Null
  [IO.File]::WriteAllText($pwFile, $password + "`n", [Text.Encoding]::ASCII)
  Write-Host "==> 访问口令已设置，保存在本机 $pwFile（已 gitignore）"
}

# ---- 6. 远端计划任务 + 启动 ----
$flags = ""
if ($Tls) { $flags += " -Tls" }
if ($NoAuth) { $flags += " -NoAuth" }
Invoke-Remote "$setup -Stage service$flags"

# ---- 7. 本机探活 ----
if ($Tls) {
  $url = "https://${RemoteIp}:$Port/"
  & uv run python -m quotaboard health --url "${url}api/ping" --ca (Join-Path $CertsDir "ca.crt") --cert (Join-Path $CertsDir "client.crt") --key (Join-Path $CertsDir "client.key")
} else {
  $url = "http://${RemoteIp}:$Port/"
  & uv run python -m quotaboard health --url "${url}api/ping"
}
if ($LASTEXITCODE -ne 0) {
  Write-Warning "从本机连不上 ${RemoteIp}:$Port（服务器本地已监听）。公网机器请检查云控制台安全组是否放行 TCP $Port。"
  exit 1
}
Write-Host "==> 部署完成：$url"
if ($Tls) { Write-Host "    浏览器需先导入 certs\client.pfx 与 ca.crt" }
if (-not $NoAuth -and (Test-Path $pwFile)) { Write-Host "    登录口令见 $pwFile" }
