@rem encoding: utf-8
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
set "FROM_REPO=0"
if exist "%ProgramFiles%\devtools\ptool\bin\ptool.bat" set "INSTALL_DIR=%ProgramFiles%\devtools\ptool"
if not defined INSTALL_DIR if exist "%ProgramFiles(x86)%\devtools\ptool\bin\ptool.bat" set "INSTALL_DIR=%ProgramFiles(x86)%\devtools\ptool"
REM No Program Files copy: a repo layout. Derive it from this script's location --
REM but flag it. Nothing here may ever delete a directory derived this way: it is
REM a checkout, and a checkout does not always carry .git (copied trees, archives,
REM CI workspaces don't), so the .git guard below is not enough on its own.
REM This once wiped a developer's working copy: the probe found bin\ptool.bat two
REM levels up, no .git was present, and rmdir /s /q took the whole tree.
if not defined INSTALL_DIR for %%i in ("%SCRIPT_DIR%\..\..") do if exist "%%~fi\bin\ptool.bat" (
    set "INSTALL_DIR=%%~fi"
    set "FROM_REPO=1"
)
if not defined INSTALL_DIR set "INSTALL_DIR=%ProgramFiles%\devtools\ptool"

echo ========================================
echo   ptool 卸载程序（Windows）
echo ========================================
echo.
echo 安装目录: %INSTALL_DIR%
echo.

if exist "%INSTALL_DIR%\unins000.exe" (
    echo 正在调用 Inno Setup 卸载程序...
    start /wait "" "%INSTALL_DIR%\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
    echo.
    REM Inno can't always delete unins000.exe itself (it's the running image), and
    REM in a headless/ssh context the self-delete handoff can be skipped entirely,
    REM leaving the exe and an empty {app} dir behind. Sweep whatever remains.
    if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%" 2>nul
    REM Drop the now-empty devtools parent too -- only when no sibling project
    REM is left (rmdir fails silently on a non-empty directory).
    for %%i in ("%INSTALL_DIR%\..") do rmdir "%%~fi" 2>nul
    echo 卸载完成。
    echo 请重新打开 CMD 窗口，PATH 变更才会生效。
    echo.
    pause
    exit /b 0
)

REM No Inno uninstaller: a repo-layout install. Confirm before removing anything.
set /p "confirm=Remove %INSTALL_DIR% and its PATH entries? (y/n): "
if /i not "!confirm!"=="y" (
    echo 已取消
    pause
    exit /b 0
)
echo.

echo [环境] 正在移除机器级 PATH 项...
REM Explicit ExpandString kind rather than Environment::SetEnvironmentVariable:
REM a machine Path that silently loses REG_EXPAND_SZ stops expanding
REM %SystemRoot%, which breaks half the entries on it.
REM try/catch so a non-elevated run reports NEED_ADMIN deterministically:
REM OpenSubKey(...,$true) throws on access denied instead of returning $null.
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $bin='%INSTALL_DIR%\bin'; $shim='%INSTALL_DIR%\shims'; $legacy='%USERPROFILE%\.devtools\ptool\shims'; function N($s){ $s.Trim().TrimEnd('\').ToUpperInvariant() }; try { $k=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SYSTEM\CurrentControlSet\Control\Session Manager\Environment',$true); if($null -eq $k){ Write-Output 'NEED_ADMIN'; exit 3 }; $p=[string]$k.GetValue('Path',''); $keep=@($p -split ';' | Where-Object { $_ -and (N $_) -ne (N $bin) -and (N $_) -ne (N $shim) }); $k.SetValue('Path', ($keep -join ';'), [Microsoft.Win32.RegistryValueKind]::ExpandString); $k.Close(); $u=[Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment',$true); if($u -and $null -ne $u.GetValue('Path')){ $up=[string]$u.GetValue('Path'); $ukeep=@($up -split ';' | Where-Object { $_ -and (N $_) -ne (N $legacy) }); $u.SetValue('Path', ($ukeep -join ';'), [Microsoft.Win32.RegistryValueKind]::ExpandString); $u.Close() }; Write-Output 'OK' } catch { if($_.Exception -is [System.UnauthorizedAccessException] -or $_.Exception -is [System.Security.SecurityException]) { Write-Output 'NEED_ADMIN'; exit 3 } else { Write-Output ('ERROR: ' + $_.Exception.Message); exit 2 } }"
if !errorlevel! equ 3 (
    echo 错误: 更新机器级 PATH 需要管理员权限。
    echo 请右键 uninstall.bat，选择「以管理员身份运行」。
    pause
    exit /b 1
)
if !errorlevel! neq 0 (
    echo 错误: 更新机器级 PATH 失败，详见上面的信息。
    pause
    exit /b 1
)
echo [完成] 机器级 PATH 已清理

if not exist "%INSTALL_DIR%" (
    echo [跳过] 安装目录不存在
    goto :uninstall_done
)

REM In the repo layout INSTALL_DIR resolves to the checkout root, so a plain
REM rmdir here would delete a developer's clone along with any uncommitted work.
REM PATH is already cleaned above, so stopping here is the whole job.
if exist "%INSTALL_DIR%\.git" (
    echo [跳过] %INSTALL_DIR% 是 git 检出目录，不删除
    echo        确实要删请手动处理
    goto :uninstall_done
)
REM Same rule, no .git needed: a directory derived from THIS script's location is
REM a source tree by construction, .git or not. A repo-layout "install" only ever
REM wrote PATH entries, so removing those is the complete uninstall.
if "%FROM_REPO%"=="1" (
    echo [跳过] %INSTALL_DIR% 是安装脚本自身的源码目录，不删除
    echo        PATH 项已在上方移除；要删目录请手动处理
    echo        确实要删的话
    goto :uninstall_done
)
REM Last guard before the destructive step: an install dir never has installer\ or
REM tests\ (only module\install.bat). Their presence means this is a source tree
REM that slipped past the two checks above.
if exist "%INSTALL_DIR%\installer" (
    echo [跳过] %INSTALL_DIR% 下有 installer\ 目录，不删除
    goto :uninstall_done
)
if exist "%INSTALL_DIR%\tests" (
    echo [跳过] %INSTALL_DIR% 下有 tests\ 目录，不删除
    goto :uninstall_done
)

rmdir /s /q "%INSTALL_DIR%"
REM Drop the now-empty devtools parent too -- only when no sibling project is
REM left (rmdir fails silently on a non-empty directory).
for %%i in ("%INSTALL_DIR%\..") do rmdir "%%~fi" 2>nul
echo [完成] 已删除 %INSTALL_DIR%

:uninstall_done
echo.
REM Clear the pre-2.2.18 layout under %USERPROFILE%\.devtools\ptool (shims /
REM completions / repo). The new layout keeps everything inside the install dir, so
REM that dotfolder is dead weight: this side only ever stripped its PATH entry,
REM while the POSIX uninstall already deletes the directories themselves
REM (module/common.sh). The parent dirs go only when EMPTY -- another tool's data
REM under %USERPROFILE%\.devtools must survive.
powershell -NoProfile -Command "$root=Join-Path $env:USERPROFILE '.devtools\ptool'; foreach ($d in 'shims','completions','repo') { Remove-Item -Recurse -Force (Join-Path $root $d) -ErrorAction SilentlyContinue }; foreach ($p in @($root, (Join-Path $env:USERPROFILE '.devtools'))) { if ((Test-Path $p) -and -not @(Get-ChildItem -Force $p).Count) { Remove-Item -Force $p -ErrorAction SilentlyContinue } }; Write-Output 'legacy ~/.devtools/ptool cleaned'"

echo.
echo ========================================
echo   卸载完成！
echo ========================================
echo.
echo 请重新打开 CMD 窗口，PATH 变更才会生效。
echo.
pause