<#
.SYNOPSIS
  在服务器上执行（由 deploy.ps1 通过 ssh 调用）：建 .venv、防火墙放行、注册开机自启的计划任务并启动、确认端口在监听。
  -Stage env      只建环境（uv sync）
  -Stage service  只做防火墙 + 计划任务 + 启动
  -Stage all      两者都做（默认）
  -Tls            HTTPS + 客户端证书（需要 certs\ca.crt server.crt server.key）；不加就是局域网明文 HTTP
  -NoAuth         不用口令
#>
param(
  [string]$Root = "C:\ps_kernel\quotaboard",
  [int]$Port = 38471,
  [string]$TaskName = "quotaboard-boot",
  [ValidateSet("all", "env", "service")][string]$Stage = "all",
  [switch]$Tls,
  [switch]$NoAuth
)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
$Root = $Root -replace '/', '\'
$python = Join-Path $Root ".venv\Scripts\python.exe"

if ($Stage -in @("all", "env")) {
  $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
  if ($uvCmd) { $uv = $uvCmd.Source } else { $uv = "C:\temp\bootstrap\uv.exe" }
  if (-not (Test-Path $uv)) { throw "找不到 uv：$uv（deploy.ps1 会把本机的 uv.exe 传到 C:\temp\bootstrap\）" }
  Write-Host "==> uv: $uv ($(& $uv --version))"
  Set-Location $Root
  New-Item -ItemType Directory -Force (Join-Path $Root "data") | Out-Null
  Write-Host "==> uv sync --frozen --no-dev（无第三方依赖，不需要出网）"
  & $uv sync --frozen --no-dev
  if ($LASTEXITCODE -ne 0) { throw "uv sync 失败" }
  if (-not (Test-Path $python)) { throw "虚拟环境未创建：$python" }
}

if ($Stage -in @("all", "service")) {
  Set-Location $Root
  $extra = ""
  if ($Tls) {
    foreach ($f in @("certs\ca.crt", "certs\server.crt", "certs\server.key")) {
      if (-not (Test-Path (Join-Path $Root $f))) { throw "缺少 $f（本机先 .\deploy\make-certs.ps1，deploy.ps1 -Tls 会上传）" }
    }
    $extra += " --cert certs\server.crt --key certs\server.key --client-ca certs\ca.crt"
  }
  if ($NoAuth) {
    $extra += " --no-auth"
    Write-Host "==> 不用口令"
  } elseif (-not (Test-Path (Join-Path $Root "data\auth.json"))) {
    throw "还没有访问口令（data\auth.json）。deploy.ps1 会设置；手动的话在服务器执行：cd $Root; .venv\Scripts\python.exe -m quotaboard set-password"
  }
  if (Test-Path (Join-Path $Root "data\LOCKDOWN.json")) {
    throw "服务处于锁定状态（连续错口令触发）。先换口令，再执行：cd $Root; .venv\Scripts\python.exe -m quotaboard unlock"
  }

  $ruleName = "quotaboard-$Port"
  if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null
    Write-Host "==> 防火墙入站规则 $ruleName 已添加"
  }

  # 计划任务：SYSTEM、开机自启、崩溃自动重启、不限时长。直接跑 .venv 里的 python，不依赖 uv。
  $logFile = Join-Path $Root "data\server.log"
  $argument = "-m quotaboard --host 0.0.0.0 --port $Port$extra --log-file `"$logFile`""
  $action = New-ScheduledTaskAction -Execute $python -Argument $argument -WorkingDirectory $Root
  $trigger = New-ScheduledTaskTrigger -AtStartup
  $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
  $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -StartWhenAvailable

  if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "==> 停止旧任务"
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
  }
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
  Start-ScheduledTask -TaskName $TaskName
  Start-Sleep -Seconds 4
  $state = (Get-ScheduledTask -TaskName $TaskName).State
  Write-Host "==> 计划任务 $TaskName 状态：$state（开机自启，崩溃 1 分钟后自动重启）"

  $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if ($listening) {
    Write-Host "==> 端口 $Port 已监听$(if ($Tls) { '（HTTPS，要求客户端证书）' } else { '（HTTP）' })"
  } else {
    Write-Warning "端口 $Port 没有监听，最近日志："
    if (Test-Path $logFile) { Get-Content $logFile -Tail 20 }
    exit 1
  }
  if (Test-Path $logFile) { Get-Content $logFile -Tail 2 }
}
