# encoding: ascii-b64
# startupctl one-click installer (Windows, PowerShell 5.1+)
#
# Usage (refreshes PATH in the current session when done):
#   irm https://raw.githubusercontent.com/CK627/MyProject/StartupItemManagement/installer/install.ps1 | iex
#
# China mirror (no VPN needed, same script, different download host):
#   irm http://101.132.165.98/dist/startupctl/install.ps1 | iex
#
# Same shape as ptool / jtool: download the source snapshot, then hand it to the
# snapshot's own "startupctl install" (user-level %USERPROFILE%\.devtools\startupctl,
# no administrator rights needed). Switch source with $env:STARTUPCTL_MIRROR='<url>'
# ('none' = GitHub only).
#
# ASCII only, and deliberately NO BOM:
#   * "irm ... | iex" passes the body to Invoke-Expression as a string. A leading BOM
#     becomes part of the first line, so PowerShell tries to run a command literally
#     named "<BOM>#" and dies with CommandNotFoundException.
#   * Non-ASCII text piped that way is decoded with the ANSI code page and arrives
#     mangled. The .bat files next to this one are ASCII-only for the same reason.
# Every Chinese message the user sees comes from Python (which owns its console
# encoding); this script speaks English on purpose.

$ErrorActionPreference = 'Stop'

# Chinese messages are embedded as UTF-8 Base64: this file is distributed
# via `irm ... | iex`, which decodes the pipe with the ANSI code page, so
# literal Chinese would arrive mangled (and a BOM breaks line 1). Keep the
# source pure ASCII.
function T([string]$b64) { [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64)) }

$mirror = if ($env:STARTUPCTL_MIRROR) { $env:STARTUPCTL_MIRROR } else { 'http://101.132.165.98/dist/startupctl' }
$github = 'https://github.com/CK627/MyProject/archive/refs/heads/StartupItemManagement.tar.gz'

function Info([string]$msg) { Write-Host "==> $msg" }
function Die([string]$msg) { Write-Host ((T '6ZSZ6K+vOiA=') + $msg) -ForegroundColor Red; exit 1 }

# ---- dependencies ----
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) { Die (T '6ZyA6KaBIFB5dGhvbiAzLjgr77yI6K+35YWI5a6J6KOF77yM5bm256Gu5L+dIHB5dGhvbiDlnKggUEFUSCDkuIrvvIk=') }
if (-not (Get-Command tar -ErrorAction SilentlyContinue)) { Die (T '6ZyA6KaBIHRhcu+8iFdpbmRvd3MgMTAgMTgwMysg6Ieq5bim77yJ') }
Info "python: $($py.Source)"

$work = Join-Path $env:TEMP ("startupctl-install-" + [System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $work -Force | Out-Null
try {
    $tgz = Join-Path $work 'src.tar.gz'
    $got = $false
    if ($mirror -ne 'none') {
        $url = "$mirror/startupctl-src.tar.gz"
        Info ((T '5q2j5Zyo5LiL6L295rqQ56CB5b+r54Wn77yI6ZWc5YOP77yJOg==') + " $url")
        try {
            Invoke-WebRequest -Uri $url -OutFile $tgz -UseBasicParsing
            if ((Get-Item $tgz).Length -gt 0) { $got = $true }
        } catch { Info (T '6ZWc5YOP5LiN5Y+v55So77yM5Zue6YCA5YiwIEdpdEh1Yg==') }
    }
    if (-not $got) {
        Info ((T '5q2j5Zyo5LiL6L295rqQ56CB5b+r54WnOg==') + " $github")
        Invoke-WebRequest -Uri $github -OutFile $tgz -UseBasicParsing
    }

    Info (T '5q2j5Zyo6Kej5Y6L')
    tar -xzf $tgz -C $work
    $src = Get-ChildItem -Path $work -Directory | Select-Object -First 1
    if (-not $src) { Die (T '5b+r54Wn57uT5p6E5byC5bi477yI6Kej5Y6L5ZCO5rKh5pyJ55uu5b2V77yJ') }

    Info ((T '5q2j5Zyo5a6J6KOF5Yiw') + " $env:USERPROFILE\.devtools\startupctl")
    $env:PYTHONPATH = $src.FullName
    & $py.Source -B -m startupctl install
    if ($LASTEXITCODE -ne 0) { Die ((T '5a6J6KOF5aSx6LSl77yI6YCA5Ye656CB') + " $LASTEXITCODE)") }

    # make it usable in this very session (new shells read the registry PATH)
    $bindir = Join-Path $env:USERPROFILE '.devtools\startupctl\bin'
    if ($env:Path -notlike "*$bindir*") { $env:Path = "$bindir;$env:Path" }
    Info (T '5a6M5oiQ44CC5Zyo5pys56qX5Y+j6K+V6K+VIHN0YXJ0dXBjdGwgLS1oZWxw')
} finally {
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}
