# encoding: ascii-b64
# jtool one-click installer (Windows, PowerShell 5.1+)
#
# Usage (refreshes PATH in the current session when done):
#   irm https://raw.githubusercontent.com/CK627/MyProject/jtool/installer/install.ps1 | iex
#
# China mirror (no VPN needed, same script, different download host):
#   irm http://101.132.165.98/dist/jtool/install.ps1 | iex
#
# Downloads the latest release .exe and installs it silently. Requires
# administrator rights (UAC prompt). Switch source with
# $env:JTOOL_MIRROR='<url>' ('none' = GitHub only).
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

# Install source: try the China mirror first, then fall back to the GitHub release.
#   * The mirror box is reachable directly from China; api.github.com is not.
#     Putting the mirror first is what makes "works without a VPN" true rather
#     than "hangs for 30 seconds and then fails".
#   * Override with $env:JTOOL_MIRROR='<url>', or 'none' to force GitHub only.
$mirror = if ($env:JTOOL_MIRROR) { $env:JTOOL_MIRROR } else { "http://101.132.165.98/dist/jtool" }

function Info([string]$msg) { Write-Host "==> $msg" }

# Fetch a release asset: mirror first, then GitHub Release.
# The mirror uses the <base>/<version>/<asset> layout, with the same asset names
# as the release.
function Get-Asset([string]$asset, [string]$ver, [string]$out) {
    if ($mirror -ne "none") {
        $murl = "$mirror/$ver/$asset"
        Info ((T '5LiL6L29') + " $murl")
        try {
            Invoke-WebRequest -Uri $murl -OutFile $out -UseBasicParsing
            if ((Get-Item $out).Length -gt 0) { return }
        } catch {
            Info (T '6ZWc5YOP5LiK5rKh5pyJ6K+l54mI5pys77yM5Zue6YCAIEdpdEh1YiBSZWxlYXNl')
        }
        Remove-Item $out -ErrorAction SilentlyContinue
    }
    $gurl = "$base/releases/download/$tool-v$ver/$asset"
    Info ((T '5LiL6L29') + " $gurl")
    Invoke-WebRequest -Uri $gurl -OutFile $out -UseBasicParsing
}

Info (T '6Kej5p6Q5pyA5paw54mI5pysLi4u')
$ver = ""

# Mirror first: VERSION is plain text, one GET is enough and much faster than
# paging the releases API.
# Read VERSION.txt, not VERSION: httpd serves an extensionless file as
# application/octet-stream, PowerShell then hands back byte[], and Trim on that
# yields nothing -- the script silently falls back to GitHub and it looks as if
# the mirror never worked. Keep the byte[] branch as a fallback too: another
# server or MIME config may still serve it as a stream.
if ($mirror -ne "none") {
    try {
        $raw = (Invoke-WebRequest -Uri "$mirror/VERSION.txt" -TimeoutSec 15 -UseBasicParsing).Content
        if ($raw -is [byte[]]) { $raw = [System.Text.Encoding]::UTF8.GetString($raw) }
        $v = ([string]$raw).Trim()
        if ($v) { $ver = $v }
    } catch {
        # Mirror unreachable; fall through to GitHub below.
    }
}

if (-not $ver) {
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
}

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
