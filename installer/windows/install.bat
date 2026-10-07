@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ptool installer (Windows)

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Layout detection:
REM   In repo: <tool>\installer\windows\ (two levels up to root)
REM   Installed: <tool>\module\ (one level up)
REM   Otherwise %PROJECT_DIR% resolves wrong after install,
REM   breaking bin\ and VERSION lookup,
REM   causing update to always report a new version.
for %%i in ("%SCRIPT_DIR%\..") do set "APP_ROOT=%%~fi"
for %%i in ("%SCRIPT_DIR%\..\..") do set "REPO_ROOT=%%~fi"
if exist "%APP_ROOT%\bin\ptool.bat" (
    set "PROJECT_DIR=%APP_ROOT%"
    set "INSTALLED=1"
) else (
    set "PROJECT_DIR=%REPO_ROOT%"
    set "INSTALLED=0"
)

REM Installed: use actual location; repo: use canonical path
if "%INSTALLED%"=="1" (
    set "INSTALL_DIR=%PROJECT_DIR%"
) else (
    set "INSTALL_DIR=C:\Program Files\devtools\ptool"
)
set "BIN_DIR=%INSTALL_DIR%\bin"
set "CONFIG_DIR=%INSTALL_DIR%\config"
set "MODULE_DIR=%INSTALL_DIR%\module"
REM Shim scripts live here, not under %USERPROFILE%. The installer prepends this
REM directory to the machine PATH: the effective PATH is machine entries first
REM and user entries after, so a user-level shims dir can never outrank a
REM python.exe that the machine PATH already points at.
set "SHIMS_DIR=%INSTALL_DIR%\shims"
set "CONFIG_FILE=%CONFIG_DIR%\ptool.conf"

REM ============================================
REM Subcommands
REM ============================================
if "%~1"=="scan" goto :do_scan
REM Non-interactive scan (for silent install)
if "%~1"=="scansilent" goto :do_scan_silent
if "%~1"=="config" goto :do_config
if "%~1"=="help" goto :do_help

REM ============================================
REM Full install
REM ============================================
echo ========================================
echo   ptool installer (Windows)
echo ========================================
echo.

echo [1/4] Copying files...
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if not exist "%MODULE_DIR%" mkdir "%MODULE_DIR%"
if not exist "%SHIMS_DIR%" mkdir "%SHIMS_DIR%"
if "%INSTALLED%"=="1" (
    echo Installed layout, skip copying
) else (
    copy "%PROJECT_DIR%\bin\ptool.bat" "%BIN_DIR%\" >nul
    if not exist "%CONFIG_FILE%" copy "%PROJECT_DIR%\config\ptool.conf" "%CONFIG_DIR%\" >nul
    REM Copy this installer to module\ for ptool install/scan
    copy "%PROJECT_DIR%\installer\windows\install.bat" "%MODULE_DIR%\install.bat" >nul
)
echo Done
echo.

echo [2/4] Setting permissions...
REM Deliberately NO write grant for anyone but administrators:
REM   config  decides which python.exe the machine-level shims run, so a writable
REM           config would let any user make an admin run an arbitrary binary.
REM   shims   sits on the machine PATH, so a writable shims dir would let any
REM           user replace a command the whole machine executes.
icacls "%INSTALL_DIR%" /grant Everyone:(OI)(CI)RX >nul 2>&1
icacls "%BIN_DIR%\ptool.bat" /grant Everyone:RX >nul 2>&1

REM /reset, not a fresh /grant. The .iss used to ask for users-modify on config
REM and dropping that line does NOT retract an ACE that is already on disk, so
REM an upgraded machine would keep the old writable config. /reset throws the
REM explicit ACEs away and lays down the inherited ones, which after the
REM Everyone:RX grant above means: administrators write, users only read.
icacls "%CONFIG_DIR%" /reset /T /C /Q >nul 2>&1
icacls "%SHIMS_DIR%" /reset /T /C /Q >nul 2>&1
echo Done
echo.

echo [3/4] Scanning and generating shims...
call :do_scan_inner
call :write_version
REM Generate shims
"%BIN_DIR%\ptool.bat" shim
echo.

echo [4/4] Configuring PATH...
REM Machine scope, and shims FIRST. Order is the whole point: the effective PATH
REM is machine entries + ';' + user entries, so anything user-level lands after
REM every machine entry. Old releases prepended the shims to the USER PATH, so a
REM python.exe already on the machine PATH kept winning and the shims were dead
REM code. This rewrites the machine Path with %SHIMS_DIR% at the front,
REM %BIN_DIR% at the back, and strips the legacy user-level entry.
REM
REM Written through the .NET registry API with an explicit ExpandString kind:
REM SetEnvironmentVariable would leave the value kind up to the framework, and a
REM machine Path that silently loses REG_EXPAND_SZ stops expanding %SystemRoot%.
REM No '!' anywhere in this one-liner: delayed expansion would swallow it.
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $shim='%SHIMS_DIR%'; $bin='%BIN_DIR%'; $legacy='%USERPROFILE%\.devtools\ptool\shims'; function N($s){ $s.Trim().TrimEnd('\').ToUpperInvariant() }; $k=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SYSTEM\CurrentControlSet\Control\Session Manager\Environment',$true); if($null -eq $k){ Write-Output 'NEED_ADMIN'; exit 3 }; $p=[string]$k.GetValue('Path',''); $keep=@($p -split ';' | Where-Object { $_ -and (N $_) -ne (N $shim) -and (N $_) -ne (N $bin) }); $k.SetValue('Path', ((@($shim)+$keep+@($bin)) -join ';'), [Microsoft.Win32.RegistryValueKind]::ExpandString); $k.Close(); $u=[Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment',$true); if($u -and $null -ne $u.GetValue('Path')){ $up=[string]$u.GetValue('Path'); $ukeep=@($up -split ';' | Where-Object { $_ -and (N $_) -ne (N $legacy) }); $u.SetValue('Path', ($ukeep -join ';'), [Microsoft.Win32.RegistryValueKind]::ExpandString); $u.Close() }; Write-Output 'OK'"

REM Check the exit code: without this a failed write (no admin) would still fall
REM through to the "Install complete" banner below, which is a lie.
if !errorlevel! equ 3 (
    echo Error: administrator privileges are required to update the machine PATH.
    echo Right-click install.bat and choose "Run as administrator".
    exit /b 1
)
if !errorlevel! neq 0 (
    echo Error: failed to update the machine PATH, see the message above.
    exit /b 1
)
echo Done
echo.
echo ========================================
echo   Install complete!
echo ========================================
echo.
echo Install dir: %INSTALL_DIR%
echo Config file: %CONFIG_FILE%
echo Please reopen a new CMD window
echo.
pause
exit /b 0

REM ============================================
REM Scan
REM ============================================
:do_scan
echo [Scan] Detecting Python path...
echo.

set "found_dir="
if exist "C:\Python*" (
    for /d %%d in (C:\Python*) do (
        if exist "%%d\python.exe" (
            set "found_dir=C:\"
            goto :scan_found
        )
    )
)
if exist "%LOCALAPPDATA%\Programs\Python" (
    set "found_dir=%LOCALAPPDATA%\Programs\Python"
    goto :scan_found
)

echo Python dir not found
set /p "found_dir=Enter Python install path: "
if not exist "!found_dir!" (
    echo Error: path does not exist
    exit /b 1
)

:scan_found
echo Found: !found_dir!
echo.
echo Installed Pythons:
for /d %%d in ("!found_dir!\Python*") do (
    if exist "%%d\python.exe" (
        for /f "tokens=*" %%v in ('"%%d\python.exe" --version 2^>^&1') do (
            echo   %%~nxd - %%v
        )
    )
)
echo.

call :write_config

echo Config written: %CONFIG_FILE%
echo.
type "%CONFIG_FILE%"
exit /b 0

:do_scan_inner
set "found_dir="
if exist "C:\Python*" (
    for /d %%d in (C:\Python*) do (
        if exist "%%d\python.exe" (
            set "found_dir=C:\"
            goto :scan_inner_found
        )
    )
)
if exist "%LOCALAPPDATA%\Programs\Python" set "found_dir=%LOCALAPPDATA%\Programs\Python"

:scan_inner_found
if not defined found_dir set "found_dir=C:\"
call :write_config
echo Written: %CONFIG_FILE%
exit /b 0

REM ============================================
REM Write config (preserve existing default version)
REM ============================================
:write_config
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if not defined found_dir set "found_dir=C:\"

REM Probe before writing. The config directory is administrator-only now, so a
REM non-elevated run would otherwise die halfway through with whatever raw error
REM cmd happens to print. Redirect first: the other order adds a trailing space.
>"%CONFIG_DIR%\.write-probe" echo ok 2>nul
if not exist "%CONFIG_DIR%\.write-probe" (
    echo Error: cannot write %CONFIG_FILE%
    echo Administrator privileges are required. Open an elevated CMD and run:
    echo   install.bat scan
    exit /b 1
)
del "%CONFIG_DIR%\.write-probe" >nul 2>&1

set "KEEP_DEFAULT=# PTOOL_DEFAULT_VERSION="3.11""
set "KEEP_VERSION=# PTOOL_VERSION="""
set "HAS_DEFAULT="
if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        REM HAS_DEFAULT is an explicit flag on purpose: the shipped template line
        REM is '# PTOOL_DEFAULT_VERSION="3.11"', so %%a is '# PTOOL_DEFAULT_VERSION'
        REM and never matches here. Testing the string instead of a flag would
        REM read that comment as a configured default.
        if "%%a"=="PTOOL_DEFAULT_VERSION" ( set "KEEP_DEFAULT=%%a=%%b" & set "HAS_DEFAULT=1" )
        if "%%a"=="PTOOL_VERSION" set "KEEP_VERSION=%%a=%%b"
    )
)

REM No default configured yet: choose one. The shims in %SHIMS_DIR% are
REM prepended to the machine PATH, so without a default every bare `python` on
REM this machine would have to fall through the runtime fallback in bin\ptool.bat.
REM The highest version found is the least surprising choice. Never overwrites a
REM default the user set -- HAS_DEFAULT guards that, so upgrades keep it.
if not defined HAS_DEFAULT (
    call :pick_best_version
    if defined BEST_VERSION (
        set "KEEP_DEFAULT=PTOOL_DEFAULT_VERSION="!BEST_VERSION!""
        echo Auto-selected default version: !BEST_VERSION!
        echo   from !found_dir!
        echo   change it with: ptool use ^<version^>
    ) else (
        echo Warning: no Python found under !found_dir!
        echo   default version left unset; shims fall back to the highest
        echo   version they find at run time
    )
)

(
    echo # ptool 配置文件
    echo.
    echo # Python 安装路径（父目录）
    echo PYTHON_BASE_DIR="!found_dir!"
    echo.
    echo # 默认版本
    echo !KEEP_DEFAULT!
    echo.
    echo # ptool 版本（由 install / update 维护，请勿手动修改）
    echo !KEEP_VERSION!
) > "%CONFIG_FILE%"
exit /b 0

REM ============================================
REM Version a Python directory name spells out (no interpreter run)
REM Dir name is Python plus 1-digit major and 1-2 digit minor, split by position
REM   Python311 -> 3.11   Python27 -> 2.7   Python312 -> 3.12
REM Deliberately identical to :ver_from_dir in bin\ptool.bat: the default written
REM here is also what that script falls back to at run time, so the two must
REM agree or a bare `python` would resolve to a different version than the one
REM the config claims is the default.
REM arg1 = directory name, arg2 = variable to receive the version
REM ============================================
:py_name_version
set "%~2="
set "_VD=%~1"
if "!_VD:~6,1!"=="" exit /b 0
set "%~2=!_VD:~6,1!.!_VD:~7,2!"
exit /b 0

REM ============================================
REM Sortable score for a version string: major*10000 + minor*100 + patch
REM   3.11 -> 31100    3.12 -> 31200    3.9 -> 30900    2.7 -> 20700
REM so 3.12 outranks 3.9 -- what a human expects and what a plain string compare
REM gets exactly backwards.
REM The three components are initialised to 0 first and the loop only overwrites
REM the ones that exist: an empty component would otherwise make `set /a` read a
REM bare `*` and fail. Passing the NAMES to `set /a` (not the values) means an
REM undefined name reads as 0 rather than raising an error.
REM arg1 = version, arg2 = variable to receive the score
REM ============================================
:ver_score
set "%~2=0"
set "_SCORE=0"
set "_SM=0"
set "_SN=0"
set "_SP=0"
for /f "tokens=1,2,3 delims=." %%a in ("%~1") do (
    if not "%%a"=="" set "_SM=%%a"
    if not "%%b"=="" set "_SN=%%b"
    if not "%%c"=="" set "_SP=%%c"
)
set /a "_SCORE=_SM*10000+_SN*100+_SP" >nul 2>&1
set "%~2=!_SCORE!"
exit /b 0

REM ============================================
REM Highest version a Python directory name under found_dir spells out.
REM Directory names only, no interpreter run: this feeds the default version, and
REM a default is also what bin\ptool.bat falls back to at run time, so it must
REM know only what :py_name_version knows -- otherwise the two would disagree.
REM Sets BEST_VERSION; leaves it empty when nothing usable is found.
REM ============================================
:pick_best_version
set "BEST_VERSION="
set "_BSCORE=-1"
if not exist "!found_dir!" exit /b 1
for /d %%d in ("!found_dir!\Python*") do (
    if exist "%%d\python.exe" (
        call :py_name_version "%%~nxd" _PV
        if defined _PV (
            call :ver_score "!_PV!" _PSC
            if !_PSC! gtr !_BSCORE! (
                set "_BSCORE=!_PSC!"
                set "BEST_VERSION=!_PV!"
            )
        )
    )
)
if defined BEST_VERSION exit /b 0
exit /b 1

REM ============================================
REM Record version
REM ============================================
:write_version
if not exist "%PROJECT_DIR%\VERSION" exit /b 0
set "VER="
for /f "usebackq tokens=*" %%v in ("%PROJECT_DIR%\VERSION") do if not defined VER set "VER=%%v"
if not defined VER exit /b 0
findstr /v /b /c:"PTOOL_VERSION=" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
REM Redirect before echo: the other order appends a trailing space.
>>"%CONFIG_FILE%.tmp" echo PTOOL_VERSION="!VER!"
move /y "%CONFIG_FILE%.tmp" "%CONFIG_FILE%" >nul
exit /b 0

REM ============================================
REM 非交互扫描（安装包静默安装时调用）
REM 复用 :do_scan_inner —— 检测不到就落到默认值，不会像 :do_scan 那样 set /p 询问
REM ============================================
:do_scan_silent
call :do_scan_inner
call :write_version
exit /b 0

REM ============================================
REM 查看配置
REM ============================================
:do_config
echo Config file: %CONFIG_FILE%
echo.
if exist "%CONFIG_FILE%" (
    type "%CONFIG_FILE%"
) else (
    echo (不存在，请运行: install.bat scan)
)
exit /b 0

REM ============================================
REM 帮助
REM ============================================
:do_help
echo ptool 安装脚本 (Windows)
echo.
echo 用法:
echo   install.bat          完整安装
echo   install.bat scan     扫描 Python 路径，更新配置
echo   install.bat config   查看配置
echo   install.bat help     帮助
exit /b 0
