# ctfsweep 一键安装脚本（Windows）
#
# 用法（PowerShell，装完自动刷新当前会话的 PATH）:
#   irm https://raw.githubusercontent.com/CK627/MyProject/CtfSweep/installer/install.ps1 | iex
#
# 国内镜像（无需 VPN，同一份脚本，只是换个下载地址）:
#   irm http://101.132.165.98/dist/ctfsweep/install.ps1 | iex
#
# 形态与 ptool / jtool 的 Windows 一键安装一致：下载源码快照 → 交给快照里的
# ctfsweep install 落地（用户级 %USERPROFILE%\.devtools\ctfsweep，不需要管理员）。
# 换源：$env:CTFSWEEP_MIRROR='<url>'（'none' = 只走 GitHub）。
#
# ⚠️ 本文件必须带 UTF-8 BOM 保存：Windows PowerShell 5.1 对无 BOM 的 .ps1 按 ANSI
#    代码页读，中文会整段乱码（.bat 也有同类坑，那边的做法是纯 ASCII）。

$ErrorActionPreference = 'Stop'

$mirror = if ($env:CTFSWEEP_MIRROR) { $env:CTFSWEEP_MIRROR } else { 'http://101.132.165.98/dist/ctfsweep' }
$github = 'https://github.com/CK627/MyProject/archive/refs/heads/CtfSweep.tar.gz'

function Info([string]$msg) { Write-Host "==> $msg" }
function Die([string]$msg) { Write-Host "错误: $msg" -ForegroundColor Red; exit 1 }

# ---- 1. 依赖检查 ----
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) { Die '需要 Python 3.8+（装好并让 python 进 PATH 后再来）' }
if (-not (Get-Command tar -ErrorAction SilentlyContinue)) { Die '需要 tar（Windows 10 1803+ 自带）' }
Info "python: $($py.Source)"

$work = Join-Path $env:TEMP ("ctfsweep-install-" + [System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $work -Force | Out-Null
try {
    $tgz = Join-Path $work 'src.tar.gz'
    $got = $false
    if ($mirror -ne 'none') {
        $url = "$mirror/ctfsweep-src.tar.gz"
        Info "下载源码快照（镜像）: $url"
        try {
            Invoke-WebRequest -Uri $url -OutFile $tgz -UseBasicParsing
            if ((Get-Item $tgz).Length -gt 0) { $got = $true }
        } catch { Info '镜像不可用，回退 GitHub' }
    }
    if (-not $got) {
        Info "下载源码快照: $github"
        Invoke-WebRequest -Uri $github -OutFile $tgz -UseBasicParsing
    }

    Info '解压'
    tar -xzf $tgz -C $work
    $src = Get-ChildItem -Path $work -Directory | Select-Object -First 1
    if (-not $src) { Die '快照结构异常（解压后没有目录）' }

    Info "安装到 $env:USERPROFILE\.devtools\ctfsweep"
    $env:PYTHONPATH = $src.FullName
    & $py.Source -B -m ctfsweep install
    if ($LASTEXITCODE -ne 0) { Die "安装失败（退出码 $LASTEXITCODE）" }

    # 当前会话立即可用（新终端靠注册表里那行 PATH）
    $bindir = Join-Path $env:USERPROFILE '.devtools\ctfsweep\bin'
    if ($env:Path -notlike "*$bindir*") { $env:Path = "$bindir;$env:Path" }
    Info '完成。当前窗口可直接敲: ctfsweep --help'
} finally {
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}
