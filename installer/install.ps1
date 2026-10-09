# ptool 一键安装脚本（Windows）
#
# 用法（PowerShell，安装后自动刷新当前会话的 PATH）:
#   irm https://raw.githubusercontent.com/CK627/MyProject/ptool/installer/install.ps1 | iex
#
# 国内镜像（无需 VPN，同一份脚本，只是换个下载地址）:
#   irm http://101.132.165.98/dist/ptool/install.ps1 | iex
#
# 会下载最新 Release 的 .exe 并静默安装。需要管理员权限（会弹 UAC）。

$ErrorActionPreference = 'Stop'

$tool = "ptool"
$base = "https://github.com/CK627/MyProject"

# 安装源：默认先走国内镜像，拿不到再回退 GitHub Release。
#   · 这台镜像机在国内直连可达，api.github.com 则不保证；把镜像放在前面，
#     「不开 VPN 也能装」才是真的，而不是「卡半分钟后失败」。
#   · 覆盖方式：$env:PTOOL_MIRROR='<url>' 换镜像地址，设成 'none' 强制只走 GitHub。
$mirror = if ($env:PTOOL_MIRROR) { $env:PTOOL_MIRROR } else { "http://101.132.165.98/dist/ptool" }

function Info([string]$msg) { Write-Host "==> $msg" }

# 下载发布资产：先镜像，再 GitHub Release。
# 镜像按 <base>/<version>/<asset> 布局，与 release 里的资产同名。
function Get-Asset([string]$asset, [string]$ver, [string]$out) {
    if ($mirror -ne "none") {
        $murl = "$mirror/$ver/$asset"
        Info "下载 $murl"
        try {
            Invoke-WebRequest -Uri $murl -OutFile $out -UseBasicParsing
            if ((Get-Item $out).Length -gt 0) { return }
        } catch {
            Info "镜像上没有该版本，回退 GitHub Release"
        }
        Remove-Item $out -ErrorAction SilentlyContinue
    }
    $gurl = "$base/releases/download/$tool-v$ver/$asset"
    Info "下载 $gurl"
    Invoke-WebRequest -Uri $gurl -OutFile $out -UseBasicParsing
}

Info "解析最新版本..."
$ver = ""

# 镜像优先：VERSION 是纯文本，一次 GET 就够，比翻 releases API 快得多。
# 读 VERSION.txt 而不是 VERSION：无扩展名的文件 httpd 会按 application/octet-stream
# 发，PowerShell 收到的是 byte[]，下面再 Trim 也拿不到字符串 —— 结果就是静默
# 回退到 GitHub，看起来像镜像根本没生效。
# 仍然做一次 byte[] 兜底：换台服务器、换个 MIME 配置就不一定还是 text。
if ($mirror -ne "none") {
    try {
        $raw = (Invoke-WebRequest -Uri "$mirror/VERSION.txt" -TimeoutSec 15 -UseBasicParsing).Content
        if ($raw -is [byte[]]) { $raw = [System.Text.Encoding]::UTF8.GetString($raw) }
        $v = ([string]$raw).Trim()
        if ($v) { $ver = $v }
    } catch {
        # 镜像不可达，下面走 GitHub
    }
}

if (-not $ver) {
    # 解析最新版本 tag（ptool-v2.2.15 -> 2.2.15）
    # 用 releases 而不是 tags：只有 release 里才有 setup exe，且这里按 100/页 翻页 ——
    # 本仓库是多项目 monorepo，tag（或 release）总数增长后单页会被截断、漏掉 ptool。
    $headers = @{ "User-Agent" = "ptool-installer" }
    $releases = @()
    $page = 1
    do {
        try {
            $batch = Invoke-RestMethod -Uri "https://api.github.com/repos/CK627/MyProject/releases?per_page=100&page=$page" -Headers $headers
        } catch {
            throw "无法访问 GitHub API：$($_.Exception.Message)"
        }
        $releases += @(@($batch) | Where-Object { $_.tag_name -like "$tool-v*" })
        $page++
    } while (@($batch).Count -eq 100 -and $page -le 5)

    if (-not $releases) { throw "未找到 $tool 的 release" }

    $version = ($releases |
        Sort-Object { [System.Version]($_.tag_name -replace "^$tool-v", "") } -Descending |
        Select-Object -First 1).tag_name
    $ver = $version -replace "^$tool-v", ""
}

if (-not $ver) { throw "未解析到 $tool 的版本号" }
Info "安装 $tool $ver"

# 下载 exe
$out = "$env:TEMP\$tool-setup-$ver.exe"
Get-Asset "$tool-setup-$ver.exe" $ver $out

# 静默安装（Inno Setup，需要管理员权限）
Info "安装（如果弹出 UAC 请点「是」）..."
$proc = Start-Process -FilePath $out -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait -PassThru
Remove-Item $out -ErrorAction SilentlyContinue

if ($proc.ExitCode -ne 0) { throw "安装失败，退出码 $($proc.ExitCode)" }

# 刷新当前会话的 PATH（安装器写了机器级 PATH，但当前会话不会自动刷新）
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

Info "$tool 安装完成，当前会话已刷新 PATH"
Info "新开的终端会自动继承安装器写入的 PATH"
