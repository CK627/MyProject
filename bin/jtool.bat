@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM jtool - Java version manager for Windows

REM ============================================
REM Paths
REM ============================================
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_DIR=%%~fi"
set "CONFIG_FILE=%PROJECT_DIR%\config\jtool.conf"

REM Install path is derived from the script location, not hardcoded.
REM The installer may target Program Files or Program Files x86,
REM depending on installer bitness; a hardcoded path breaks update.
set "INSTALL_DIR=%PROJECT_DIR%"
set "BIN_DIR=%INSTALL_DIR%\bin"
set "CONFIG_DIR=%INSTALL_DIR%\config"
set "MODULE_DIR=%INSTALL_DIR%\module"

REM Locate install.bat: installed layout, repo layout, legacy root
set "INSTALL_MODULE=%PROJECT_DIR%\module\install.bat"
if not exist "%INSTALL_MODULE%" set "INSTALL_MODULE=%PROJECT_DIR%\installer\windows\install.bat"
if not exist "%INSTALL_MODULE%" set "INSTALL_MODULE=%PROJECT_DIR%\install.bat"

REM ============================================
REM Load config
REM ============================================
set "JAVA_BASE_DIR="
set "JTOOL_DEFAULT_VERSION="

if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        set "key=%%a"
        set "val=%%b"
        if not "!key:~0,1!"=="#" if not "!key!"=="" (
            set "val=!val:"=!"
            call :trim_sp val
            if "!key!"=="JAVA_BASE_DIR" set "JAVA_BASE_DIR=!val!"
            if "!key!"=="JTOOL_DEFAULT_VERSION" set "JTOOL_DEFAULT_VERSION=!val!"
        )
    )
)

REM ============================================
REM Main dispatch
REM ============================================
if "%~1"=="" goto :show_help

if "%~1"=="list" goto :list_jdks
if "%~1"=="help" goto :show_help
if "%~1"=="-h" goto :show_help
if "%~1"=="--help" goto :show_help
if "%~1"=="use" goto :cmd_use
if "%~1"=="current" goto :cmd_current
if "%~1"=="home" goto :cmd_home
if "%~1"=="info" goto :cmd_info
if "%~1"=="tools" goto :cmd_tools
if "%~1"=="run" goto :cmd_run
if "%~1"=="scan" goto :cmd_scan
if "%~1"=="config" goto :cmd_config
if "%~1"=="install" goto :cmd_install
if "%~1"=="update" goto :cmd_update
if "%~1"=="uninstall" goto :cmd_uninstall
if "%~1"=="shim" goto :cmd_shim

REM Run a tool
set "tool=%~1"
if "!JAVA_BASE_DIR!"=="" (
    echo Error: JAVA_BASE_DIR not set
    echo Run: jtool scan
    exit /b 1
)

set "version=%~2"

REM A version always starts with a digit; a missing second argument, or one
REM starting with - or /, is an argument rather than a version, so fall back
REM to the default version. A shim forwarding `java -version` is exactly this
REM shape: tool plus argument, no version.
if "!version!"=="" goto :use_default_version
set "_vfirst=!version:~0,1!"
if "!_vfirst!"=="-" goto :use_default_version
if "!_vfirst!"=="/" goto :use_default_version

shift /1
shift /1
goto :run_tool

:use_default_version
if not "!JTOOL_DEFAULT_VERSION!"=="" (
    set "version=!JTOOL_DEFAULT_VERSION!"
    shift /1
    goto :run_tool
)

REM No default configured. Bailing out here would break bare `java` for every
REM user on the machine: the installed layout PREPENDS this tool's shims to the
REM machine PATH, so this is exactly the path a plain `java` takes. Fall back to
REM the highest version a directory NAME spells out. Directory names only, never
REM a subprocess, so this cannot travel back out through a shim.
call :best_dir_version version
if not "!version!"=="" (
    shift /1
    goto :run_tool
)

echo Error: need tool name and version
echo No default version is set and no JDK was found under !JAVA_BASE_DIR!
echo Run: jtool use ^<version^>
exit /b 1

:run_tool
call :resolve_jdk "!version!" jdk_home
if not defined jdk_home (
    echo Error: JDK !version! not found
    echo Base dir: !JAVA_BASE_DIR!
    echo Run "jtool scan" or fix JAVA_BASE_DIR
    exit /b 1
)
set "tool_path=!jdk_home!\bin\!tool!"

if not exist "!tool_path!.exe" (
    if not exist "!tool_path!" (
        echo Error: JDK !version! has no !tool! tool
        exit /b 1
    )
)

REM %* does not change with shift; it still carries the tool name and version,
REM so the remaining arguments are rebuilt here
set "TOOL_ARGS="
:collect_args
if "%~1"=="" goto :args_ready
set "TOOL_ARGS=!TOOL_ARGS! %1"
shift /1
goto :collect_args
:args_ready

"!tool_path!" !TOOL_ARGS!
exit /b !errorlevel!

REM ============================================
REM List JDKs
REM ============================================
:list_jdks
if "!JAVA_BASE_DIR!"=="" (
    echo Error: JAVA_BASE_DIR not set
    echo Run: jtool scan
    exit /b 1
)

echo Java path: !JAVA_BASE_DIR!
echo.
echo Installed JDKs:
set "found=0"
for /d %%d in ("!JAVA_BASE_DIR!\*") do (
    call :jdk_home_of "%%d" _LH
    if defined _LH (
        call :jdk_name_version "%%~nxd" _LV
        if not defined _LV set "_LV=%%~nxd"
        for /f "tokens=*" %%v in ('"!_LH!\bin\java.exe" -version 2^>^&1 ^| findstr /i version') do (
            echo   !_LV! - %%v
            set "found=1"
        )
    )
)
if "!found!"=="0" echo   None found
echo.
if not "!JTOOL_DEFAULT_VERSION!"=="" echo Default: !JTOOL_DEFAULT_VERSION!
exit /b 0

REM ============================================
REM Help
REM ============================================
:show_help
echo jtool - Java version manager for Windows
echo.
echo Usage:
echo   jtool ^<tool^> ^<version^> [args...]   Run a tool
echo   jtool list                          List JDKs
echo   jtool use ^<version^>                Set default version
echo   jtool current                       Show current version
echo   jtool home ^<version^>               Show JAVA_HOME
echo   jtool info ^<version^>               Show details
echo   jtool tools ^<version^>              List tools
echo   jtool run ^<version^> ^<file.java^>  Compile and run
echo   jtool scan                          Scan Java paths
echo   jtool config                        Show config
echo   jtool install                       Full install
echo   jtool update                        Check and update
echo   jtool uninstall [-y]                Uninstall (-y silent)
echo   jtool shim                          Rebuild shims
echo   jtool help                          Show help
exit /b 0

:cmd_use
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
call :resolve_jdk "%~2" use_home
if not defined use_home ( echo Error: JDK %~2 not found & exit /b 1 )

REM The config directory is administrator-only (it decides which java.exe the
REM machine-level shims run). Probe before writing so a non-elevated call gets a
REM usable message instead of a raw "Access is denied" from cmd. Redirect first:
REM the other order adds a trailing space to the probe file, which does not
REM matter here but keeps the pattern consistent across the file.
>"%CONFIG_DIR%\.write-probe" echo ok 2>nul
if not exist "%CONFIG_DIR%\.write-probe" (
    echo Error: cannot write %CONFIG_FILE%
    echo Administrator privileges are required. Open an elevated CMD and run:
    echo   jtool use %~2
    exit /b 1
)
del "%CONFIG_DIR%\.write-probe" >nul 2>&1

REM Update the config file
findstr /v "JTOOL_DEFAULT_VERSION" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
REM Redirect before echo: the other order appends a trailing space.
>>"%CONFIG_FILE%.tmp" echo JTOOL_DEFAULT_VERSION="%~2"
move /y "%CONFIG_FILE%.tmp" "%CONFIG_FILE%" >nul
set "JTOOL_DEFAULT_VERSION=%~2"
echo Default version set: %~2
echo JAVA_HOME: !use_home!
exit /b 0

REM ============================================
REM current
REM ============================================
:cmd_current
if "!JTOOL_DEFAULT_VERSION!"=="" ( echo No default version & exit /b 1 )
call :resolve_jdk "!JTOOL_DEFAULT_VERSION!" cur_home
echo Default: !JTOOL_DEFAULT_VERSION!
if defined cur_home (
    echo JAVA_HOME: !cur_home!
) else (
    echo JAVA_HOME: not found, run jtool scan
)
exit /b 0

REM ============================================
REM home
REM ============================================
:cmd_home
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
call :resolve_jdk "%~2" home_path
if not defined home_path ( echo Error: JDK %~2 not found & exit /b 1 )
echo !home_path!
exit /b 0

REM ============================================
REM info
REM ============================================
:cmd_info
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
call :resolve_jdk "%~2" info_home
if not defined info_home ( echo Error: JDK %~2 not found & exit /b 1 )
echo === JDK %~2 ===
echo JAVA_HOME: !info_home!
echo.
"!info_home!\bin\java.exe" -version 2>&1
echo.
echo Tools:
for %%f in ("!info_home!\bin\*") do echo   %%~nxf
exit /b 0

REM ============================================
REM tools
REM ============================================
:cmd_tools
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
call :resolve_jdk "%~2" tools_home
if not defined tools_home ( echo Error: JDK %~2 not found & exit /b 1 )
echo JDK %~2 tools:
for %%f in ("!tools_home!\bin\*") do echo   %%~nxf
exit /b 0

REM ============================================
REM run
REM ============================================
:cmd_run
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
if "%~3"=="" ( echo Error: specify a file & exit /b 1 )
set "java_file=%~3"
if not exist "!java_file!" ( echo Error: file not found & exit /b 1 )
call :resolve_jdk "%~2" run_home
if not defined run_home ( echo Error: JDK %~2 not found & exit /b 1 )

for %%f in ("!java_file!") do set "class_name=%%~nf"
echo === Compile (JDK %~2) ===
"!run_home!\bin\javac.exe" "!java_file!"
if !errorlevel! neq 0 ( echo Compile failed & exit /b 1 )
echo.
echo === Run ===
"!run_home!\bin\java.exe" "!class_name!"
set "exit_code=!errorlevel!"
if exist "!class_name!.class" del "!class_name!.class"
exit /b !exit_code!

REM ============================================
REM scan
REM ============================================
:cmd_scan
call "%INSTALL_MODULE%" scan
exit /b !errorlevel!

REM ============================================
REM config
REM ============================================
:cmd_config
echo Config file: %CONFIG_FILE%
echo.
if exist "%CONFIG_FILE%" ( type "%CONFIG_FILE%" ) else ( echo (not found, run: jtool scan) )
exit /b 0

REM ============================================
REM install
REM ============================================
:cmd_install
call "%INSTALL_MODULE%"
exit /b !errorlevel!

REM ============================================
REM update
REM ============================================
:cmd_update
REM Writing to the install dir needs admin; request elevation when not admin
net session >nul 2>&1
if !errorlevel! neq 0 (
    echo update needs admin, requesting elevation...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList 'update' -Verb RunAs"
    exit /b 0
)
REM Prefer curl+tar; fall back to git
where curl >nul 2>&1
if !errorlevel! neq 0 goto :update_via_git
where tar >nul 2>&1
if !errorlevel! neq 0 goto :update_via_git
goto :update_via_curl

REM ============================================
REM update via curl + tar (no git needed)
REM ============================================
:update_via_curl
echo Checking for updates...
set "REMOTE_VERSION="
for /f "usebackq delims=" %%v in (`powershell -NoProfile -Command "(Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/CK627/MyProject/jtool/VERSION').Content.Trim()"`) do set "REMOTE_VERSION=%%v"
if "!REMOTE_VERSION!"=="" for /f "usebackq delims=" %%v in (`curl -fsSL "https://raw.githubusercontent.com/CK627/MyProject/jtool/VERSION" 2^>nul`) do if not defined REMOTE_VERSION set "REMOTE_VERSION=%%v"
if "!REMOTE_VERSION!"=="" (
    echo Version read failed, falling back to git...
    goto :update_via_git
)

set "LOCAL_VERSION="
if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        if "%%a"=="JTOOL_VERSION" set "LOCAL_VERSION=%%~b"
    )
)
if defined LOCAL_VERSION set "LOCAL_VERSION=!LOCAL_VERSION:"=!"
if defined LOCAL_VERSION set "LOCAL_VERSION=!LOCAL_VERSION: =!"

if "!LOCAL_VERSION!"=="!REMOTE_VERSION!" (
    echo Already up to date ^(v!LOCAL_VERSION!^)
    exit /b 0
)

echo New version: v!LOCAL_VERSION! -> v!REMOTE_VERSION!

set "UPD_TMP=%TEMP%\jtool-update"
rmdir /s /q "%UPD_TMP%" 2>nul
mkdir "%UPD_TMP%"

echo Downloading update...
powershell -NoProfile -Command "Invoke-WebRequest -UseBasicParsing 'https://github.com/CK627/MyProject/archive/refs/heads/jtool.tar.gz' -OutFile '%UPD_TMP%\src.tar.gz'"
if not exist "%UPD_TMP%\src.tar.gz" curl -fsSL "https://github.com/CK627/MyProject/archive/refs/heads/jtool.tar.gz" -o "%UPD_TMP%\src.tar.gz"
if not exist "%UPD_TMP%\src.tar.gz" ( echo Download failed, fallback to git & goto :update_via_git )

tar -xzf "%UPD_TMP%\src.tar.gz" -C "%UPD_TMP%"
if !errorlevel! neq 0 ( echo Extract failed & exit /b 1 )

set "SRC=%UPD_TMP%\MyProject-jtool"

copy /y "!SRC!\bin\jtool.bat" "%BIN_DIR%\" >nul
if !errorlevel! neq 0 (
    echo Error: cannot write %BIN_DIR%
    echo Please run as administrator
    exit /b 1
)
if exist "!SRC!\installer\windows\install.bat" (
    copy /y "!SRC!\installer\windows\install.bat" "%MODULE_DIR%\install.bat" >nul
)
if not exist "%CONFIG_FILE%" copy "!SRC!\config\jtool.conf" "%CONFIG_DIR%\" >nul

findstr /v /b /c:"JTOOL_VERSION=" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
REM Redirect before echo: the other order appends a trailing space.
>>"%CONFIG_FILE%.tmp" echo JTOOL_VERSION="!REMOTE_VERSION!"
move /y "%CONFIG_FILE%.tmp" "%CONFIG_FILE%" >nul

rmdir /s /q "%UPD_TMP%" 2>nul

echo Update complete!
echo   Version: v!LOCAL_VERSION! -> v!REMOTE_VERSION!
exit /b 0

REM ============================================
REM update via git (fallback)
REM ============================================
:update_via_git
where git >nul 2>&1
if !errorlevel! neq 0 (
    echo Error: no git and no curl/tar, cannot update
    exit /b 1
)

set "REPO_DIR=%USERPROFILE%\.devtools\jtool\repo"
set "FRESH_CLONE=0"

if not exist "!REPO_DIR!\.git" (
    echo First update, cloning repo...
    git clone --branch jtool --single-branch --depth 1 https://github.com/CK627/MyProject.git "!REPO_DIR!"
    if !errorlevel! neq 0 ( echo Clone failed & exit /b 1 )
    set "FRESH_CLONE=1"
)

set "REMOTE_VERSION="
if "!FRESH_CLONE!"=="1" (
    for /f "usebackq tokens=*" %%v in ("!REPO_DIR!\VERSION") do if not defined REMOTE_VERSION set "REMOTE_VERSION=%%v"
) else (
    echo Checking for updates...
    git -C "!REPO_DIR!" fetch origin jtool 2>nul
    if !errorlevel! neq 0 ( echo Fetch failed, check network & exit /b 1 )
    for /f "usebackq tokens=*" %%v in (`git -C "!REPO_DIR!" show origin/jtool:VERSION 2^>nul`) do if not defined REMOTE_VERSION set "REMOTE_VERSION=%%v"
)
if "!REMOTE_VERSION!"=="" ( echo Error: cannot get version & exit /b 1 )

set "LOCAL_VERSION="
if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        if "%%a"=="JTOOL_VERSION" set "LOCAL_VERSION=%%~b"
    )
)
if defined LOCAL_VERSION set "LOCAL_VERSION=!LOCAL_VERSION:"=!"
if defined LOCAL_VERSION set "LOCAL_VERSION=!LOCAL_VERSION: =!"

if "!LOCAL_VERSION!"=="!REMOTE_VERSION!" (
    echo Already up to date ^(v!LOCAL_VERSION!^)
    exit /b 0
)

echo New version: v!LOCAL_VERSION! -> v!REMOTE_VERSION!

if "!FRESH_CLONE!"=="0" (
    git -C "!REPO_DIR!" checkout jtool 2>nul
    git -C "!REPO_DIR!" pull origin jtool
    if !errorlevel! neq 0 ( echo Pull failed & exit /b 1 )
)

copy /y "!REPO_DIR!\bin\jtool.bat" "%BIN_DIR%\" >nul
if !errorlevel! neq 0 (
    echo Error: cannot write %BIN_DIR%
    echo Please run as administrator
    exit /b 1
)
if exist "!REPO_DIR!\installer\windows\install.bat" (
    copy /y "!REPO_DIR!\installer\windows\install.bat" "%MODULE_DIR%\install.bat" >nul
)
if not exist "%CONFIG_FILE%" copy "!REPO_DIR!\config\jtool.conf" "%CONFIG_DIR%\" >nul

findstr /v /b /c:"JTOOL_VERSION=" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
REM Redirect before echo: the other order appends a trailing space.
>>"%CONFIG_FILE%.tmp" echo JTOOL_VERSION="!REMOTE_VERSION!"
move /y "%CONFIG_FILE%.tmp" "%CONFIG_FILE%" >nul

echo Update complete!
echo   Version: v!LOCAL_VERSION! -> v!REMOTE_VERSION!
exit /b 0

REM ============================================
REM uninstall
REM ============================================
:cmd_uninstall
if "%~2"=="-y" goto :uninstall_silent
if exist "%INSTALL_DIR%\unins000.exe" (
    start "" "%INSTALL_DIR%\unins000.exe"
    echo Uninstaller started, confirm in dialog
) else (
    echo Uninstaller not found %INSTALL_DIR%\unins000.exe
    echo Uninstall via Control Panel - Add or Remove Programs
)
exit /b 0

:uninstall_silent
if exist "%INSTALL_DIR%\unins000.exe" (
    start /wait "" "%INSTALL_DIR%\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
    echo Uninstall complete
) else (
    echo Uninstaller not found %INSTALL_DIR%\unins000.exe
)
exit /b 0

REM ============================================
REM shim
REM ============================================
:cmd_shim
REM Installed layout puts the shims in %INSTALL_DIR%\shims, which the installer
REM PREPENDS to the machine PATH. That is the whole point: the effective PATH is
REM machine entries first and user entries after, so a shim living in the user
REM PATH can never outrank Oracle's machine-level javapath. module\install.bat
REM only exists after install.bat copied it there, so its presence is what tells
REM the two layouts apart -- INSTALL_MODULE cannot, it falls back to the repo
REM path and is therefore always defined.
REM Repo layout keeps the per-user dir so a checkout stays usable without admin.
set "SHIMS_DIR=%USERPROFILE%\.devtools\jtool\shims"
set "SHIMS_SCOPE=user"
if exist "%PROJECT_DIR%\module\install.bat" (
    set "SHIMS_DIR=%PROJECT_DIR%\shims"
    set "SHIMS_SCOPE=machine"
)

if not exist "!SHIMS_DIR!" mkdir "!SHIMS_DIR!" 2>nul

REM Real write probe. mkdir can succeed and the write still fail (read-only
REM dir, no admin), so the probe is what actually decides. Redirect first: the
REM other order appends a trailing space to the file.
>"!SHIMS_DIR!\.shim-probe" echo ok 2>nul
if not exist "!SHIMS_DIR!\.shim-probe" (
    echo Error: cannot write !SHIMS_DIR!
    echo Administrator privileges are required. Open an elevated CMD and run:
    echo   jtool shim
    exit /b 1
)
del "!SHIMS_DIR!\.shim-probe" >nul 2>&1

REM Shims are thin forwards; jtool resolves the JDK path itself, so the path
REM logic lives only in :resolve_jdk and is never duplicated into each shim
for %%t in (java javac jar jshell javadoc javap) do (
    (
        echo @echo off
        echo REM jtool shim - auto generated
        echo set "CONFIG_FILE=!CONFIG_FILE!"
        echo for %%%%i in ^("%%CONFIG_FILE%%\..\.."^) do set "JTOOL_ROOT=%%%%~fi"
        echo if not exist "%%JTOOL_ROOT%%\bin\jtool.bat" ^(
        echo     echo jtool: %%JTOOL_ROOT%%\bin\jtool.bat not found ^>^&2
        echo     exit /b 1
        echo ^)
        echo "%%JTOOL_ROOT%%\bin\jtool.bat" %%t %%*
    ) > "!SHIMS_DIR!\%%t.bat"
)

echo Shims created: !SHIMS_DIR!

if "!SHIMS_SCOPE!"=="machine" (
    REM Put on the machine PATH by the installer -- the Registry section in the
    REM .iss and the 4th step in install.bat. Doing it here too would need admin
    REM and would race the installer, so it is deliberately left out.
    REM No brackets or parens in these comment lines on purpose: this is a
    REM parenthesised block, and cmd counts a closing paren in a REM as ending
    REM it.
    echo Scope: machine ^(prepended to the machine PATH by the installer^)
    exit /b 0
)

REM Repo layout: no installer involved, so place the dir on the user PATH here.
REM This cannot outrank a machine-level java.exe, which is why the installed
REM layout uses %INSTALL_DIR%\shims instead of this directory.
powershell -NoProfile -Command "$d = Join-Path $env:USERPROFILE '.devtools\jtool\shims'; $p = [Environment]::GetEnvironmentVariable('Path','User'); $parts = @($p -split ';' | Where-Object { $_ -and ($_ -ne $d) }); [Environment]::SetEnvironmentVariable('Path', ($d + ';' + ($parts -join ';')).TrimEnd(';'), 'User'); Write-Output 'shims moved to front of user PATH'"
exit /b 0

REM ============================================
REM Resolve a version to its JDK home
REM
REM Three stages, cheap to expensive:
REM   1. deterministic candidate paths, tried in order, no subprocess
REM   2. match the version the directory NAME spells out, still no subprocess
REM   3. ask each JDK what version it really reports (java -version)
REM
REM Stages 1 and 2 keep the java shim's hot path free of subprocesses; stage 3
REM is the backstop for names that disagree with what is installed inside.
REM
REM arg1 = version, arg2 = variable to receive the home; empty if not found
REM ============================================
:resolve_jdk
set "%~2="
set "_JVER=%~1"
if "!_JVER!"=="" exit /b 1
if "!JAVA_BASE_DIR!"=="" exit /b 1
if "!_JVER!"=="8" set "_JVER=1.8"

REM Fast path: known layouts first, no java run
call :jdk_home_of "!JAVA_BASE_DIR!\jdk-!_JVER!.jdk" _JH
if defined _JH ( set "%~2=!_JH!" & exit /b 0 )
call :jdk_home_of "!JAVA_BASE_DIR!\jdk-!_JVER!" _JH
if defined _JH ( set "%~2=!_JH!" & exit /b 0 )
call :jdk_home_of "!JAVA_BASE_DIR!\!_JVER!.jdk" _JH
if defined _JH ( set "%~2=!_JH!" & exit /b 0 )
call :jdk_home_of "!JAVA_BASE_DIR!\!_JVER!" _JH
if defined _JH ( set "%~2=!_JH!" & exit /b 0 )

REM Stage 2: match on the version the directory name spells out, no java run.
REM JDK dir names differ per vendor and per distro:
REM   jdk-21.jdk / jdk-21            Oracle, Adoptium, SDKMAN
REM   temurin-21.jdk / zulu-17.0.9   vendor builds
REM   java-17-openjdk-amd64          Debian / Ubuntu
REM   java-1.8.0-openjdk             RHEL / Fedora
for /d %%d in ("!JAVA_BASE_DIR!\*") do (
    call :jdk_home_of "%%d" _JH
    if defined _JH (
        call :jdk_name_version "%%~nxd" _NV
        if defined _NV (
            call :ver_match "!_JVER!" "!_NV!" _OK
            if "!_OK!"=="1" (
                set "%~2=!_JH!"
                exit /b 0
            )
        )
    )
)

REM Stage 3: ask each JDK for the version it really reports
for /d %%d in ("!JAVA_BASE_DIR!\*") do (
    call :jdk_home_of "%%d" _JH
    if defined _JH (
        call :jdk_version_matches "!_JVER!" "%%d" _OK
        if "!_OK!"=="1" (
            set "%~2=!_JH!"
            exit /b 0
        )
    )
)
exit /b 1

REM ============================================
REM Candidate dir to JDK home: bundle layout first, then flat
REM arg1 = candidate dir, arg2 = variable to receive the home
REM ============================================
:jdk_home_of
set "%~2="
if exist "%~1\Contents\Home\bin\java.exe" ( set "%~2=%~1\Contents\Home" & exit /b 0 )
if exist "%~1\bin\java.exe" ( set "%~2=%~1" & exit /b 0 )
exit /b 1

REM ============================================
REM Version a JDK directory name spells out (no java run)
REM Splitting on letters, hyphen and underscore leaves the version as the first
REM token, so vendor prefixes and distro suffixes fall away:
REM   jdk-21.jdk -> 21             temurin-21.jdk -> 21
REM   zulu-17.0.9 -> 17.0.9        java-17-openjdk-amd64 -> 17
REM   jdk1.8.0_392 -> 1.8.0        amazon-corretto-21.jdk -> 21
REM arg1 = directory name, arg2 = variable to receive the version; empty when
REM the name spells no version at all (e.g. Homebrew's openjdk.jdk)
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
REM Sortable score for a version string: major*10000 + minor*100 + patch
REM   21 -> 210000    24 -> 240000    17.0.9 -> 170009    1.8.0 -> 10800
REM so 24 outranks 1.8.0 and 21 outranks 17.0.9 -- what a human expects and
REM what a plain string compare gets exactly backwards.
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
REM Highest version spelled out by a directory name under JAVA_BASE_DIR
REM Used as the runtime fallback when no default version is configured, so a
REM machine whose config lost its default still resolves `java` instead of
REM failing for every user. Directory names only -- no java run -- which keeps
REM this off the shim -> jtool -> shim recursion path.
REM arg1 = variable to receive the version; empty when none is usable
REM ============================================
:best_dir_version
set "%~1="
set "_BV="
set "_BSCORE=-1"
if "!JAVA_BASE_DIR!"=="" exit /b 1
for /d %%d in ("!JAVA_BASE_DIR!\*") do (
    call :jdk_home_of "%%d" _BH
    if defined _BH (
        call :jdk_name_version "%%~nxd" _BNV
        if defined _BNV (
            call :ver_score "!_BNV!" _BSC
            if !_BSC! gtr !_BSCORE! (
                set "_BSCORE=!_BSC!"
                set "_BV=!_BNV!"
            )
        )
    )
)
if defined _BV set "%~1=!_BV!"
exit /b 0

REM ============================================
REM Real version reported by the JDK in a dir; 1.8.0_491 becomes 1.8
REM arg1 = candidate dir, arg2 = variable to receive the version
REM ============================================
:jdk_real_version
set "%~2="
call :jdk_home_of "%~1" _RJH
if not defined _RJH exit /b 1
set "_RV="
for /f "tokens=3" %%v in ('"!_RJH!\bin\java.exe" -version 2^>^&1 ^| findstr /i version') do (
    if not defined _RV set "_RV=%%~v"
)
if not defined _RV (
    set "_RJH="
    exit /b 1
)
if "!_RV:~0,2!"=="1." (
    for /f "tokens=1,2 delims=." %%a in ("!_RV!") do set "_RV=%%a.%%b"
)
set "%~2=!_RV!"
set "_RJH="
exit /b 0

REM ============================================
REM Do two version strings refer to the same JDK?
REM Exact match, or the requested one is a dotted component prefix of the
REM candidate: 21 matches 21.0.7, and 1.8 matches 1.8.0_392
REM arg1 = requested, arg2 = candidate version, arg3 = variable set to 1 on match
REM ============================================
:ver_match
set "%~3=0"
set "_req=%~1"
set "_REAL=%~2"
if "!_req!"=="8" set "_req=1.8"
if "!_req!"=="" exit /b 0
if "!_REAL!"=="" exit /b 0
if "!_req!"=="_REAL!" ( set "%~3=1" & exit /b 0 )

REM Compare only the dotted components the request actually pins, so 21
REM matches 21.0.7 and 1.8 matches 1.8.0_392, while 21.0.1 does not match
REM 21.0.7. Empty request components are skipped rather than compared.
set "_qa="
set "_qb="
set "_qc="
for /f "tokens=1,2,3 delims=._" %%a in ("!_req!") do (
    set "_qa=%%a"
    set "_qb=%%b"
    set "_qc=%%c"
)
set "_ra="
set "_rb="
set "_rc="
for /f "tokens=1,2,3 delims=._" %%a in ("!_REAL!") do (
    set "_ra=%%a"
    set "_rb=%%b"
    set "_rc=%%c"
)
set "_REAL="

if not "!_qa!"=="!_ra!" exit /b 0
if defined _qb if not "!_qb!"=="!_rb!" exit /b 0
if defined _qc if not "!_qc!"=="!_rc!" exit /b 0
set "%~3=1"
exit /b 0

REM ============================================
REM Same comparison, but read the candidate version out of the dir (runs java)
REM arg1 = requested, arg2 = candidate dir, arg3 = variable set to 1 on match
REM ============================================
:jdk_version_matches
set "%~3=0"
call :jdk_real_version "%~2" _REAL
call :ver_match "%~1" "!_REAL!" %~3
exit /b 0

REM ============================================
REM Trim leading and trailing spaces from the variable named by the first
REM argument, in place.
REM
REM Writing a config line as "echo VALUE" followed by the redirect appends a
REM trailing space to the value, so a version read back can be "21 " -- which
REM then matches no JDK at all. Configs already on disk were written that way,
REM so trimming on read, not only on write, is what repairs them.
REM
REM Takes a variable NAME rather than a value on purpose: CALL re-parses its
REM argument, which would expand any environment variable inside a path.
REM ============================================
:trim_sp
set "_ts=!%~1!"
if not defined _ts exit /b 0
:trim_sp_lead
if "!_ts:~0,1!"==" " ( set "_ts=!_ts:~1!" & goto :trim_sp_lead )
:trim_sp_tail
if "!_ts:~-1!"==" " ( set "_ts=!_ts:~0,-1!" & goto :trim_sp_tail )
set "%~1=!_ts!"
exit /b 0
