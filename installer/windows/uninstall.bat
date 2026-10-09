@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM jtool uninstaller (Windows)
REM
REM The Inno Setup uninstaller is authoritative, and this script delegates to it.
REM unins000.exe removes BOTH machine PATH entries ({app}\bin and {app}\shims),
REM strips the legacy user-level entry, and deletes the directory tree.
REM
REM Doing that by hand is exactly how the previous version of this file went
REM wrong: it only knew how to strip {app}\bin from the USER PATH, so it would
REM have left both machine PATH entries behind, and its rmdir on {app} took
REM unins000.exe with it, orphaning the Add/Remove Programs registration.
REM
REM The manual path at the bottom is the fallback for repo-layout installs,
REM which have no unins000.exe.

REM Prefer the real installed copy. A repo checkout also contains bin\jtool.bat,
REM so probing that first would clean PATH entries for the repo (no-ops), leave
REM the actual machine PATH entries behind, and still report success.
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "INSTALL_DIR="
set "FROM_REPO=0"
if exist "%ProgramFiles%\devtools\jtool\bin\jtool.bat" set "INSTALL_DIR=%ProgramFiles%\devtools\jtool"
if not defined INSTALL_DIR if exist "%ProgramFiles(x86)%\devtools\jtool\bin\jtool.bat" set "INSTALL_DIR=%ProgramFiles(x86)%\devtools\jtool"
REM No Program Files copy: a repo layout. Derive it from this script's location --
REM but flag it. Nothing here may ever delete a directory derived this way: it is
REM a checkout, and a checkout does not always carry .git (copied trees, archives,
REM CI workspaces don't), so the .git guard below is not enough on its own.
REM This once wiped a developer's working copy: the probe found bin\jtool.bat two
REM levels up, no .git was present, and rmdir /s /q took the whole tree.
if not defined INSTALL_DIR for %%i in ("%SCRIPT_DIR%\..\..") do if exist "%%~fi\bin\jtool.bat" (
    set "INSTALL_DIR=%%~fi"
    set "FROM_REPO=1"
)
if not defined INSTALL_DIR set "INSTALL_DIR=%ProgramFiles%\devtools\jtool"

echo ========================================
echo   jtool uninstaller (Windows)
echo ========================================
echo.
echo Install dir: %INSTALL_DIR%
echo.

if exist "%INSTALL_DIR%\unins000.exe" (
    echo Delegating to the Inno Setup uninstaller...
    start /wait "" "%INSTALL_DIR%\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
    echo.
    REM Inno can't always delete unins000.exe itself (it's the running image), and
    REM in a headless/ssh context the self-delete handoff can be skipped entirely,
    REM leaving the exe and an empty {app} dir behind. Sweep whatever remains.
    if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%" 2>nul
    REM Drop the now-empty devtools parent too -- only when no sibling project
    REM is left (rmdir fails silently on a non-empty directory).
    for %%i in ("%INSTALL_DIR%\..") do rmdir "%%~fi" 2>nul
    echo Uninstall complete.
    echo Please reopen a CMD window for the PATH change to take effect.
    echo.
    pause
    exit /b 0
)

REM No Inno uninstaller: a repo-layout install. Confirm before removing anything.
set /p "confirm=Remove %INSTALL_DIR% and its PATH entries? (y/n): "
if /i not "!confirm!"=="y" (
    echo Cancelled
    pause
    exit /b 0
)
echo.

echo [Env] Removing machine PATH entries...
REM Explicit ExpandString kind rather than Environment::SetEnvironmentVariable:
REM a machine Path that silently loses REG_EXPAND_SZ stops expanding
REM %SystemRoot%, which breaks half the entries on it.
REM try/catch so a non-elevated run reports NEED_ADMIN deterministically:
REM OpenSubKey(...,$true) throws on access denied instead of returning $null.
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $bin='%INSTALL_DIR%\bin'; $shim='%INSTALL_DIR%\shims'; $legacy='%USERPROFILE%\.devtools\jtool\shims'; function N($s){ $s.Trim().TrimEnd('\').ToUpperInvariant() }; try { $k=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SYSTEM\CurrentControlSet\Control\Session Manager\Environment',$true); if($null -eq $k){ Write-Output 'NEED_ADMIN'; exit 3 }; $p=[string]$k.GetValue('Path',''); $keep=@($p -split ';' | Where-Object { $_ -and (N $_) -ne (N $bin) -and (N $_) -ne (N $shim) }); $k.SetValue('Path', ($keep -join ';'), [Microsoft.Win32.RegistryValueKind]::ExpandString); $k.Close(); $u=[Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment',$true); if($u -and $null -ne $u.GetValue('Path')){ $up=[string]$u.GetValue('Path'); $ukeep=@($up -split ';' | Where-Object { $_ -and (N $_) -ne (N $legacy) }); $u.SetValue('Path', ($ukeep -join ';'), [Microsoft.Win32.RegistryValueKind]::ExpandString); $u.Close() }; Write-Output 'OK' } catch { if($_.Exception -is [System.UnauthorizedAccessException] -or $_.Exception -is [System.Security.SecurityException]) { Write-Output 'NEED_ADMIN'; exit 3 } else { Write-Output ('ERROR: ' + $_.Exception.Message); exit 2 } }"
if !errorlevel! equ 3 (
    echo Error: administrator privileges are required to update the machine PATH.
    echo Right-click uninstall.bat and choose "Run as administrator".
    pause
    exit /b 1
)
if !errorlevel! neq 0 (
    echo Error: failed to update the machine PATH, see the message above.
    pause
    exit /b 1
)
echo [Done] Machine PATH cleaned

if not exist "%INSTALL_DIR%" (
    echo [Skip] Install dir not found
    goto :uninstall_done
)

REM In the repo layout INSTALL_DIR resolves to the checkout root, so a plain
REM rmdir here would delete a developer's clone along with any uncommitted work.
REM PATH is already cleaned above, so stopping here is the whole job.
if exist "%INSTALL_DIR%\.git" (
    echo [Skip] %INSTALL_DIR% is a git checkout, not deleting it
    echo        Delete it by hand if you really want it gone
    goto :uninstall_done
)
REM Same rule, no .git needed: a directory derived from THIS script's location is
REM a source tree by construction, .git or not. A repo-layout "install" only ever
REM wrote PATH entries, so removing those is the complete uninstall.
if "%FROM_REPO%"=="1" (
    echo [Skip] %INSTALL_DIR% holds this installer's own source, not deleting it
    echo        PATH entries are already removed above; delete the tree by hand
    echo        if you really want it gone
    goto :uninstall_done
)
REM Last guard before the destructive step: an install dir never has installer\ or
REM tests\ (only module\install.bat). Their presence means this is a source tree
REM that slipped past the two checks above.
if exist "%INSTALL_DIR%\installer" (
    echo [Skip] %INSTALL_DIR% has an installer\ directory, not deleting it
    goto :uninstall_done
)
if exist "%INSTALL_DIR%\tests" (
    echo [Skip] %INSTALL_DIR% has a tests\ directory, not deleting it
    goto :uninstall_done
)

rmdir /s /q "%INSTALL_DIR%"
REM Drop the now-empty devtools parent too -- only when no sibling project is
REM left (rmdir fails silently on a non-empty directory).
for %%i in ("%INSTALL_DIR%\..") do rmdir "%%~fi" 2>nul
echo [Done] Removed %INSTALL_DIR%

:uninstall_done
echo.
echo ========================================
echo   Uninstall complete!
echo ========================================
echo.
echo Please reopen a CMD window for the PATH change to take effect.
echo.
pause
