@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM jtool installer (Windows)

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
if exist "%APP_ROOT%\bin\jtool.bat" (
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
    set "INSTALL_DIR=C:\Program Files\devtools\jtool"
)
set "BIN_DIR=%INSTALL_DIR%\bin"
set "CONFIG_DIR=%INSTALL_DIR%\config"
set "MODULE_DIR=%INSTALL_DIR%\module"
REM Shim scripts live here, not under %USERPROFILE%. The installer prepends this
REM directory to the machine PATH: the effective PATH is machine entries first
REM and user entries after, so a user-level shims dir can never outrank the
REM javapath Oracle writes into the machine PATH.
set "SHIMS_DIR=%INSTALL_DIR%\shims"
set "CONFIG_FILE=%CONFIG_DIR%\jtool.conf"

REM ============================================
REM Subcommands
REM ============================================
if "%~1"=="scan" goto :do_scan
if "%~1"=="scansilent" goto :do_scan_silent
if "%~1"=="config" goto :do_config
if "%~1"=="help" goto :do_help

REM ============================================
REM Full install
REM ============================================
echo ========================================
echo   jtool installer (Windows)
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
    copy "%PROJECT_DIR%\bin\jtool.bat" "%BIN_DIR%\" >nul
    if not exist "%CONFIG_FILE%" copy "%PROJECT_DIR%\config\jtool.conf" "%CONFIG_DIR%\" >nul
    REM Copy this installer into module\ so jtool install / jtool scan can call it
    copy "%PROJECT_DIR%\installer\windows\install.bat" "%MODULE_DIR%\install.bat" >nul
    REM Lay down VERSION too: a fresh repo install otherwise has no VERSION in the
    REM install dir, so the first update would print "v(unknown) -> vX" noise.
    if exist "%PROJECT_DIR%\VERSION" copy "%PROJECT_DIR%\VERSION" "%INSTALL_DIR%\" >nul
)
echo Done
echo.

echo [2/4] Setting permissions...
REM Deliberately NO write grant for anyone but administrators:
REM   config  decides which java.exe the machine-level shims run, so a writable
REM           config would let any user make an admin run an arbitrary binary.
REM   shims   sits on the machine PATH, so a writable shims dir would let any
REM           user replace a command the whole machine executes.
icacls "%INSTALL_DIR%" /grant Everyone:(OI)(CI)RX >nul 2>&1
icacls "%BIN_DIR%\jtool.bat" /grant Everyone:RX >nul 2>&1

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
if errorlevel 1 exit /b 1
call :write_version
"%BIN_DIR%\jtool.bat" shim
echo.

echo [4/4] Configuring PATH...
REM Machine scope, and shims FIRST. Order is the whole point: the effective PATH
REM is machine entries + ';' + user entries, so anything user-level lands after
REM every machine entry. Oracle drops javapath into the machine PATH, so old
REM releases that prepended the shims to the USER PATH never won and bare `java`
REM kept resolving to Oracle's. This rewrites the machine Path with %SHIMS_DIR%
REM at the front, %BIN_DIR% at the back, and strips the legacy user-level entry.
REM
REM Written through the .NET registry API with an explicit ExpandString kind:
REM SetEnvironmentVariable would leave the value kind up to the framework, and a
REM machine Path that silently loses REG_EXPAND_SZ stops expanding %SystemRoot%.
REM No '!' anywhere in this one-liner: delayed expansion would swallow it.
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $shim='%SHIMS_DIR%'; $bin='%BIN_DIR%'; $legacy='%USERPROFILE%\.devtools\jtool\shims'; function N($s){ $s.Trim().TrimEnd('\').ToUpperInvariant() }; $k=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SYSTEM\CurrentControlSet\Control\Session Manager\Environment',$true); if($null -eq $k){ Write-Output 'NEED_ADMIN'; exit 3 }; $p=[string]$k.GetValue('Path',''); $keep=@($p -split ';' | Where-Object { $_ -and (N $_) -ne (N $shim) -and (N $_) -ne (N $bin) }); $k.SetValue('Path', ((@($shim)+$keep+@($bin)) -join ';'), [Microsoft.Win32.RegistryValueKind]::ExpandString); $k.Close(); $u=[Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment',$true); if($u -and $null -ne $u.GetValue('Path')){ $up=[string]$u.GetValue('Path'); $ukeep=@($up -split ';' | Where-Object { $_ -and (N $_) -ne (N $legacy) }); $u.SetValue('Path', ($ukeep -join ';'), [Microsoft.Win32.RegistryValueKind]::ExpandString); $u.Close() }; Write-Output 'OK'"

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
echo [Scan] Detecting Java path...
echo.

call :find_java_base found_dir

if not defined found_dir (
    echo Java dir not found
    set /p "found_dir=Enter Java install path: "
    if not exist "!found_dir!" (
        echo Error: path does not exist
        exit /b 1
    )
)

:scan_found
echo Found: !found_dir!
echo.
echo Installed JDKs:
call :list_jdks_of "!found_dir!"
echo.

call :write_config
if errorlevel 1 exit /b 1

echo Config written: %CONFIG_FILE%
echo.
type "%CONFIG_FILE%"
exit /b 0

:do_scan_inner
call :find_java_base found_dir
if not defined found_dir set "found_dir=C:\Program Files\Java"
call :write_config
if errorlevel 1 exit /b 1
echo Written: %CONFIG_FILE%
exit /b 0

REM ============================================
REM Vendor roots the official installers use. Oracle's docs put each JDK in
REM %ProgramFiles%\Java\jdk-<feature>; Adoptium, Microsoft, Azul and AWS each
REM ship their own root. The first root that actually holds a JDK wins, so the
REM order below is the priority order.
REM arg1 = variable to receive the root; left empty when none holds a JDK
REM ============================================
:find_java_base
set "%~1="
call :probe_base "C:\Program Files\Java" %~1
if defined %~1 exit /b 0
call :probe_base "C:\Program Files\Eclipse Adoptium" %~1
if defined %~1 exit /b 0
call :probe_base "C:\Program Files\Microsoft" %~1
if defined %~1 exit /b 0
call :probe_base "C:\Program Files\Zulu" %~1
if defined %~1 exit /b 0
call :probe_base "C:\Program Files\Amazon Corretto" %~1
if defined %~1 exit /b 0
call :probe_base "%LOCALAPPDATA%\Programs\Eclipse Adoptium" %~1
if defined %~1 exit /b 0
exit /b 1

REM ============================================
REM Does arg1 hold any JDK? Native installers put one directory per JDK
REM directly under the vendor root, so the marker is a child with bin\java.exe
REM arg2 = variable to receive arg1 when it does hold one; empty otherwise
REM ============================================
:probe_base
set "%~2="
if not exist "%~1" exit /b 1
for /d %%d in ("%~1\*") do (
    if exist "%%d\bin\java.exe" (
        set "%~2=%~1"
        exit /b 0
    )
)
exit /b 1

REM ============================================
REM Installed JDKs under a base dir, with the version each one reports
REM arg1 = base dir
REM ============================================
:list_jdks_of
for /d %%d in ("%~1\*") do (
    if exist "%%d\bin\java.exe" (
        call :jdk_name_version "%%~nxd" _SNV
        if not defined _SNV set "_SNV=%%~nxd"
        for /f "tokens=*" %%v in ('"%%d\bin\java.exe" -version 2^>^&1 ^| findstr /i version') do (
            echo   !_SNV! - %%v
        )
    )
)
exit /b 0

REM ============================================
REM Version a JDK directory name spells out (no java run)
REM Splitting on letters, hyphen and underscore leaves the version as the first
REM token: jdk-21.jdk -> 21, temurin-21.jdk -> 21, openjdk-17 -> 17
REM arg1 = directory name, arg2 = variable to receive the version
REM ============================================
:jdk_name_version
set "%~2="
set "_NN=%~1"
if "!_NN:~-4!"==".jdk" set "_NN=!_NN:~0,-4!"
set "_NV="
for /f "tokens=1 delims=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_" %%a in ("!_NN!") do set "_NV=%%a"
if not defined _NV exit /b 1
if "!_NV:~-1!"=="." set "_NV=!_NV:~0,-1!"
if not defined _NV exit /b 1
set "%~2=!_NV!"
exit /b 0

REM ============================================
REM Write config (preserve existing default version)
REM ============================================
:write_config
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if not defined found_dir set "found_dir=C:\Program Files\Java"

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

set "KEEP_DEFAULT=# JTOOL_DEFAULT_VERSION="21""
set "KEEP_VERSION=# JTOOL_VERSION="""
set "HAS_DEFAULT="
if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        REM HAS_DEFAULT is an explicit flag on purpose: the shipped template line
        REM is '# JTOOL_DEFAULT_VERSION="21"', so %%a is '# JTOOL_DEFAULT_VERSION'
        REM and never matches here. Testing the string instead of a flag would
        REM read that comment as a configured default.
        if "%%a"=="JTOOL_DEFAULT_VERSION" ( set "KEEP_DEFAULT=%%a=%%b" & set "HAS_DEFAULT=1" )
        if "%%a"=="JTOOL_VERSION" set "KEEP_VERSION=%%a=%%b"
    )
)

REM No default configured yet: choose one. The shims in %SHIMS_DIR% are
REM prepended to the machine PATH, so without a default every bare `java` on this
REM machine would have to fall through the runtime fallback in bin\jtool.bat.
REM The highest version found is the least surprising choice. Never overwrites a
REM default the user set -- HAS_DEFAULT guards that, so upgrades keep it.
if not defined HAS_DEFAULT (
    call :pick_best_version
    if defined BEST_VERSION (
        set "KEEP_DEFAULT=JTOOL_DEFAULT_VERSION="!BEST_VERSION!""
        echo Auto-selected default version: !BEST_VERSION!
        echo   from !found_dir!
        echo   change it with: jtool use ^<version^>
    ) else (
        echo Warning: no JDK found under !found_dir!
        echo   default version left unset; shims fall back to the highest
        echo   version they find at run time
    )
)

(
    echo # jtool configuration
    echo.
    echo # Java base directory (the parent directory)
    echo JAVA_BASE_DIR="!found_dir!"
    echo.
    echo # Default version
    echo !KEEP_DEFAULT!
    echo.
    echo # jtool version (maintained by install / update, do not edit)
    echo !KEEP_VERSION!
) > "%CONFIG_FILE%"
exit /b 0

REM ============================================
REM Sortable score for a version string: major*10000 + minor*100 + patch
REM   21 -> 210000    24 -> 240000    17.0.9 -> 170009    1.8.0 -> 10800
REM so 24 outranks 1.8.0 and 21 outranks 17.0.9 -- what a human expects and what
REM a plain string compare gets exactly backwards.
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
REM Highest version a JDK directory name under found_dir spells out.
REM Directory names only, no java run: this feeds the default version, and a
REM default is also what bin\jtool.bat falls back to at run time, so it must
REM know only what :jdk_name_version knows -- otherwise the two would disagree.
REM Sets BEST_VERSION; leaves it empty when nothing usable is found.
REM ============================================
:pick_best_version
set "BEST_VERSION="
set "_BSCORE=-1"
if not exist "!found_dir!" exit /b 1
for /d %%d in ("!found_dir!\*") do (
    if exist "%%d\bin\java.exe" (
        call :jdk_name_version "%%~nxd" _PV
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
REM Record jtool version
REM ============================================
:write_version
if not exist "%PROJECT_DIR%\VERSION" exit /b 0
set "VER="
for /f "usebackq tokens=*" %%v in ("%PROJECT_DIR%\VERSION") do if not defined VER set "VER=%%v"
if not defined VER exit /b 0
findstr /v /b /c:"JTOOL_VERSION=" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
REM Redirect before echo: the other order appends a trailing space.
>>"%CONFIG_FILE%.tmp" echo JTOOL_VERSION="!VER!"
move /y "%CONFIG_FILE%.tmp" "%CONFIG_FILE%" >nul
exit /b 0

REM ============================================
REM Non-interactive scan, for the installer package in silent mode
REM Reuses :do_scan_inner, which falls back to a default instead of
REM prompting the way :do_scan does
REM ============================================
:do_scan_silent
call :do_scan_inner
if errorlevel 1 exit /b 1
call :write_version
exit /b 0

REM ============================================
REM Show config
REM ============================================
:do_config
echo Config file: %CONFIG_FILE%
echo.
if exist "%CONFIG_FILE%" (
    type "%CONFIG_FILE%"
) else (
    echo (not found, run: install.bat scan)
)
exit /b 0

REM ============================================
REM Help
REM ============================================
:do_help
echo jtool installer (Windows)
echo.
echo Usage:
echo   install.bat          Full install
echo   install.bat scan     Scan Java path, update config
echo   install.bat config   Show config
echo   install.bat help     Show help
exit /b 0
