@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ptool uninstaller (Windows)
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

REM Prefer the real installed copy. A repo checkout also contains bin\ptool.bat,
REM so probing that first would clean PATH entries for the repo (no-ops), leave
REM the actual machine PATH entries behind, and still report success.
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "INSTALL_DIR="
if exist "%ProgramFiles%\devtools\ptool\bin\ptool.bat" set "INSTALL_DIR=%ProgramFiles%\devtools\ptool"
if not defined INSTALL_DIR if exist "%ProgramFiles(x86)%\devtools\ptool\bin\ptool.bat" set "INSTALL_DIR=%ProgramFiles(x86)%\devtools\ptool"
REM No Program Files copy: a repo layout. Derive it from this script's location.
if not defined INSTALL_DIR for %%i in ("%SCRIPT_DIR%\..\..") do if exist "%%~fi\bin\ptool.bat" set "INSTALL_DIR=%%~fi"
if not defined INSTALL_DIR set "INSTALL_DIR=%ProgramFiles%\devtools\ptool"

echo ========================================
echo   ptool uninstaller (Windows)
echo ========================================
echo.
echo Install dir: %INSTALL_DIR%
echo.

if exist "%INSTALL_DIR%\unins000.exe" (
    echo Delegating to the Inno Setup uninstaller...
    start /wait "" "%INSTALL_DIR%\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
    echo.
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
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $bin='%INSTALL_DIR%\bin'; $shim='%INSTALL_DIR%\shims'; $legacy='%USERPROFILE%\.devtools\ptool\shims'; function N($s){ $s.Trim().TrimEnd('\').ToUpperInvariant() }; try { $k=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SYSTEM\CurrentControlSet\Control\Session Manager\Environment',$true); if($null -eq $k){ Write-Output 'NEED_ADMIN'; exit 3 }; $p=[string]$k.GetValue('Path',''); $keep=@($p -split ';' | Where-Object { $_ -and (N $_) -ne (N $bin) -and (N $_) -ne (N $shim) }); $k.SetValue('Path', ($keep -join ';'), [Microsoft.Win32.RegistryValueKind]::ExpandString); $k.Close(); $u=[Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment',$true); if($u -and $null -ne $u.GetValue('Path')){ $up=[string]$u.GetValue('Path'); $ukeep=@($up -split ';' | Where-Object { $_ -and (N $_) -ne (N $legacy) }); $u.SetValue('Path', ($ukeep -join ';'), [Microsoft.Win32.RegistryValueKind]::ExpandString); $u.Close() }; Write-Output 'OK' } catch { if($_.Exception -is [System.UnauthorizedAccessException] -or $_.Exception -is [System.Security.SecurityException]) { Write-Output 'NEED_ADMIN'; exit 3 } else { Write-Output ('ERROR: ' + $_.Exception.Message); exit 2 } }"
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

rmdir /s /q "%INSTALL_DIR%"
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
