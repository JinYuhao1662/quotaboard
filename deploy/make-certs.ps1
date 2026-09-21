<#
.SYNOPSIS
  生成一套私有 CA + 服务端证书 + 客户端证书（mTLS 用），输出到 certs/（已 gitignore）。需要 openssl（Git for Windows 自带）。
  客户端证书就是「本地密钥」：把 client.pfx 导入到你要用的每台电脑 / 手机，没有它连登录页都打不开。
.EXAMPLE
  .\deploy\make-certs.ps1                                  # 服务端 SAN 默认 139.159.214.28 + 127.0.0.1 + localhost
  .\deploy\make-certs.ps1 -ServerIps 1.2.3.4 -ClientName my-laptop
#>
param(
  [string]$OutDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "certs"),
  [string[]]$ServerIps = @("139.159.214.28", "127.0.0.1"),
  [string[]]$ServerDns = @("localhost"),
  [string]$ClientName = "quotaboard-client",
  [int]$Days = 1095
)
$ErrorActionPreference = "Stop"

$openssl = (Get-Command openssl -ErrorAction SilentlyContinue).Source
if (-not $openssl) {
  foreach ($c in @("C:\Program Files\Git\usr\bin\openssl.exe", "C:\Program Files\Git\mingw64\bin\openssl.exe")) {
    if (Test-Path $c) { $openssl = $c; break }
  }
}
if (-not $openssl) { throw "找不到 openssl.exe（Git for Windows 自带，或自行安装 OpenSSL）" }

function Invoke-OpenSsl {
  # openssl 把进度写到 stderr；PowerShell 5.1 在 Stop 模式下会把重定向的 stderr 当异常，所以这里临时改回 Continue 并只看退出码
  $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  $out = & $openssl @args 2>&1
  $ErrorActionPreference = $prev
  if ($LASTEXITCODE -ne 0) { throw "openssl 失败：$($args -join ' ')`n$($out -join "`n")" }
}

New-Item -ItemType Directory -Force $OutDir | Out-Null
Push-Location $OutDir
try {
  if (Test-Path "ca.key") { throw "$OutDir 已有 ca.key。为避免覆盖正在使用的证书，不重复生成；要重做请先删掉该目录。" }
  $san = (($ServerIps | ForEach-Object { "IP:$_" }) + ($ServerDns | ForEach-Object { "DNS:$_" })) -join ","

  Write-Host "==> CA"
  # openssl 自带配置的 v3_ca 已经给 -x509 加了 basicConstraints=CA:TRUE，再 -addext 会重复导致证书无效，这里只补 keyUsage
  Invoke-OpenSsl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout ca.key -out ca.crt -days 3650 `
    -subj "/CN=quotaboard-ca" -addext "keyUsage=critical,keyCertSign,cRLSign"

  Write-Host "==> 服务端证书  SAN=$san"
  Invoke-OpenSsl req -new -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout server.key -out server.csr -subj "/CN=quotaboard-server"
  Set-Content -Path server.ext -Encoding ascii -Value "subjectAltName=$san`nextendedKeyUsage=serverAuth`nkeyUsage=digitalSignature,keyEncipherment"
  Invoke-OpenSsl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days $Days -extfile server.ext

  Write-Host "==> 客户端证书  CN=$ClientName"
  Invoke-OpenSsl req -new -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout client.key -out client.csr -subj "/CN=$ClientName"
  Set-Content -Path client.ext -Encoding ascii -Value "extendedKeyUsage=clientAuth`nkeyUsage=digitalSignature"
  Invoke-OpenSsl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days $Days -extfile client.ext

  $pfxPass = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
  Invoke-OpenSsl pkcs12 -export -inkey client.key -in client.crt -certfile ca.crt -out client.pfx -passout "pass:$pfxPass"
  Set-Content -Path client-pfx-password.txt -Encoding ascii -Value $pfxPass

  Remove-Item server.csr, client.csr, server.ext, client.ext, ca.srl -ErrorAction SilentlyContinue
} finally { Pop-Location }

Write-Host ""
Write-Host "已生成到 $OutDir："
Write-Host "  ca.crt / ca.key            私有 CA（ca.key 只留在本机，别上传）"
Write-Host "  server.crt / server.key    服务端证书（部署脚本会连同 ca.crt 一起传到服务器）"
Write-Host "  client.crt / client.key    客户端证书（python -m quotaboard health 用）"
Write-Host "  client.pfx                 导入到电脑 / 手机的客户端证书，导入口令在 client-pfx-password.txt"
Write-Host ""
Write-Host "导入（Windows）：双击 client.pfx → 当前用户 → 输入口令 → 自动选择存储；再双击 ca.crt → 安装到「受信任的根证书颁发机构」，浏览器就不再警告。"
