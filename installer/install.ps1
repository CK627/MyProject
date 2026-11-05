# encoding: ascii-b64
# jtool one-click installer (Windows, PowerShell 5.1+)
#
# Usage (refreshes PATH in the current session when done):
#   irm https://raw.githubusercontent.com/CK627/MyProject/jtool/installer/install.ps1 | iex
#
# raw.githubusercontent.com is frequently reset on mainland networks (curl 35 /
# connection timeout). The same file is also served by api.github.com; use that
# URL when raw fails:
#   irm "https://api.github.com/repos/CK627/MyProject/contents/installer/install.ps1?ref=jtool" `
#     -Headers @{ Accept = 'application/vnd.github.raw' } | iex
#
# Downloads the latest release .exe and installs it silently. Requires
# administrator rights (UAC prompt).
#
# ASCII only, and deliberately NO BOM:
#   * "irm ... | iex" passes the body to Invoke-Expression as a string. A leading BOM
#     becomes part of the first line, so PowerShell tries to run a command literally
#     named "<BOM>#" and dies with CommandNotFoundException.
#   * Non-ASCII text piped that way is decoded with the ANSI code page and arrives
#     mangled. Keep the source pure ASCII; the .bat files next to this one follow
#     the same rule.
# Chinese messages the user sees are embedded as UTF-8 Base64 and decoded at
# runtime by T() below.

$ErrorActionPreference = 'Stop'

# Chinese messages are embedded as UTF-8 Base64: this file is distributed
# via `irm ... | iex`, which decodes the pipe with the ANSI code page, so
# literal Chinese would arrive mangled (and a BOM breaks line 1). Keep the
# source pure ASCII.
function T([string]$b64) { [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64)) }

$tool = "jtool"
$base = "https://github.com/CK627/MyProject"

function Info([string]$msg) { Write-Host "==> $msg" }

# Fetch a release asset from the GitHub release.
function Get-Asset([string]$asset, [string]$ver, [string]$out) {
    $gurl = "$base/releases/download/$tool-v$ver/$asset"
    Info ((T '5LiL6L29') + " $gurl")
    Invoke-WebRequest -Uri $gurl -OutFile $out -UseBasicParsing
}

Info (T '6Kej5p6Q5pyA5paw54mI5pysLi4u')
$ver = ""

# Resolve the newest release tag (jtool-v2.2.15 -> 2.2.15).
# Use releases rather than tags: only releases carry the setup exe, and page
# through at 100 per page -- this repo is a monorepo, so once the total tag
# (or release) count grows a single page gets truncated and jtool falls off.
$headers = @{ "User-Agent" = "jtool-installer" }
$releases = @()
$page = 1
do {
    try {
        $batch = Invoke-RestMethod -Uri "https://api.github.com/repos/CK627/MyProject/releases?per_page=100&page=$page" -Headers $headers
    } catch {
        throw ((T '5peg5rOV6K6/6ZeuIEdpdEh1YiBBUEnvvJo=') + $($_.Exception.Message))
    }
    $releases += @(@($batch) | Where-Object { $_.tag_name -like "$tool-v*" })
    $page++
} while (@($batch).Count -eq 100 -and $page -le 5)

if (-not $releases) { throw ((T '5pyq5om+5YiwIA==') + "$tool" + (T 'IOeahCByZWxlYXNl')) }

$version = ($releases |
    Sort-Object { [System.Version]($_.tag_name -replace "^$tool-v", "") } -Descending |
    Select-Object -First 1).tag_name
$ver = $version -replace "^$tool-v", ""

if (-not $ver) { throw ((T '5pyq6Kej5p6Q5YiwIA==') + "$tool" + (T 'IOeahOeJiOacrOWPtw==')) }
Info ((T '5a6J6KOFIA==') + "$tool $ver")

# Download the exe
$out = "$env:TEMP\$tool-setup-$ver.exe"
Get-Asset "$tool-setup-$ver.exe" $ver $out

# Silent install (Inno Setup, needs administrator rights)
Info (T '5a6J6KOF77yI5aaC5p6c5by55Ye6IFVBQyDor7fngrnjgIzmmK/jgI3vvIkuLi4=')
$proc = Start-Process -FilePath $out -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait -PassThru
Remove-Item $out -ErrorAction SilentlyContinue

if ($proc.ExitCode -ne 0) { throw ((T '5a6J6KOF5aSx6LSl77yM6YCA5Ye656CBIA==') + $($proc.ExitCode)) }

# Refresh PATH in this session (the installer writes the machine-level PATH but
# the current session does not pick it up automatically)
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

Info ("$tool" + (T 'IOWuieijheWujOaIkO+8jOW9k+WJjeS8muivneW3suWIt+aWsCBQQVRI'))
Info (T '5paw5byA55qE57uI56uv5Lya6Ieq5Yqo57un5om/5a6J6KOF5Zmo5YaZ5YWl55qEIFBBVEg=')
