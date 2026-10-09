# ptool 一键安装脚本（Windows）
#
# 用法（PowerShell，安装后自动刷新当前会话的 PATH）:
#   irm https://raw.githubusercontent.com/CK627/MyProject/ptool/installer/install.ps1 | iex
#
# 会下载最新 Release 的 .exe 并静默安装。需要管理员权限（会弹 UAC）。

$ErrorActionPreference = 'Stop'

$tool = "ptool"
$base = "https://github.com/CK627/MyProject"

function Info([string]$msg) { Write-Host "==> $msg" }

# 解析最新版本 tag（ptool-v2.2.15 -> 2.2.15）
# 用 releases 而不是 tags：只有 release 里才有 setup exe，且这里按 100/页 翻页 ——
# 本仓库是多项目 monorepo，tag（或 release）总数增长后单页会被截断、漏掉 ptool。
Info "解析最新版本..."
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
Info "安装 $tool $ver"

# 下载 exe
$url = "$base/releases/download/$version/$tool-setup-$ver.exe"
$out = "$env:TEMP\$tool-setup-$ver.exe"
Info "下载 $url"
Invoke-WebRequest -Uri $url -OutFile $out

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
