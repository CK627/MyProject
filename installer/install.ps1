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

$mirror = if ($env:STARTUPCTL_MIRROR) { $env:STARTUPCTL_MIRROR } else { 'http://101.132.165.98/dist/startupctl' }
$github = 'https://github.com/CK627/MyProject/archive/refs/heads/StartupItemManagement.tar.gz'

function Info([string]$msg) { Write-Host "==> $msg" }
function Die([string]$msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

# ---- dependencies ----
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) { Die 'Python 3.8+ required (install it and make sure python is on PATH)' }
if (-not (Get-Command tar -ErrorAction SilentlyContinue)) { Die 'tar required (bundled with Windows 10 1803+)' }
Info "python: $($py.Source)"

$work = Join-Path $env:TEMP ("startupctl-install-" + [System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $work -Force | Out-Null
try {
    $tgz = Join-Path $work 'src.tar.gz'
    $got = $false
    if ($mirror -ne 'none') {
        $url = "$mirror/startupctl-src.tar.gz"
        Info "downloading snapshot (mirror): $url"
        try {
            Invoke-WebRequest -Uri $url -OutFile $tgz -UseBasicParsing
            if ((Get-Item $tgz).Length -gt 0) { $got = $true }
        } catch { Info 'mirror unavailable, falling back to GitHub' }
    }
    if (-not $got) {
        Info "downloading snapshot: $github"
        Invoke-WebRequest -Uri $github -OutFile $tgz -UseBasicParsing
    }

    Info 'extracting'
    tar -xzf $tgz -C $work
    $src = Get-ChildItem -Path $work -Directory | Select-Object -First 1
    if (-not $src) { Die 'unexpected snapshot layout (no directory after extraction)' }

    Info "installing to $env:USERPROFILE\.devtools\startupctl"
    $env:PYTHONPATH = $src.FullName
    & $py.Source -B -m startupctl install
    if ($LASTEXITCODE -ne 0) { Die "install failed (exit code $LASTEXITCODE)" }

    # make it usable in this very session (new shells read the registry PATH)
    $bindir = Join-Path $env:USERPROFILE '.devtools\startupctl\bin'
    if ($env:Path -notlike "*$bindir*") { $env:Path = "$bindir;$env:Path" }
    Info 'done. Try "startupctl --help" in this window.'
} finally {
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}
