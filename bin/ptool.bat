@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ptool - Python version manager for Windows

REM ============================================
REM Paths
REM ============================================
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_DIR=%%~fi"
set "CONFIG_FILE=%PROJECT_DIR%\config\ptool.conf"

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
set "PYTHON_BASE_DIR="
set "PTOOL_DEFAULT_VERSION="

if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        set "key=%%a"
        set "val=%%b"
        if not "!key:~0,1!"=="#" if not "!key!"=="" (
            set "val=!val:"=!"
            call :trim_sp val
            if "!key!"=="PYTHON_BASE_DIR" set "PYTHON_BASE_DIR=!val!"
            if "!key!"=="PTOOL_DEFAULT_VERSION" set "PTOOL_DEFAULT_VERSION=!val!"
        )
    )
)

REM ============================================
REM Main dispatch
REM ============================================
if "%~1"=="" goto :show_help

if "%~1"=="list" goto :list_pythons
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
set "version=%~2"

REM 版本号总是数字开头；若第二个参数缺失、或以 - / 开头（是参数不是版本号），
REM 则用默认版本。shim 转发 `python -V` 就是「工具 + 参数、无版本号」的形式。
if "!version!"=="" goto :use_default_version
set "_vfirst=!version:~0,1!"
if "!_vfirst!"=="-" goto :use_default_version
if "!_vfirst!"=="/" goto :use_default_version

shift /1
shift /1
goto :run_tool

:use_default_version
if not "!PTOOL_DEFAULT_VERSION!"=="" (
    set "version=!PTOOL_DEFAULT_VERSION!"
    shift /1
    goto :run_tool
) else (
    echo Error: need tool name and version
    exit /b 1
)

:run_tool
call :resolve_py "!version!" python_exe
if not defined python_exe (
    echo Error: Python !version! not found
    echo Base dir: !PYTHON_BASE_DIR!
    echo Run "ptool scan" or edit PYTHON_BASE_DIR
    exit /b 1
)

REM Args do not change with shift; rebuild remaining args here
set "TOOL_ARGS="
:collect_args
if "%~1"=="" goto :args_ready
set "TOOL_ARGS=!TOOL_ARGS! %1"
shift /1
goto :collect_args
:args_ready

if "!tool!"=="python"  ( "!python_exe!" !TOOL_ARGS! & exit /b !errorlevel! )
if "!tool!"=="python3" ( "!python_exe!" !TOOL_ARGS! & exit /b !errorlevel! )
if "!tool!"=="pip"     ( "!python_exe!" -m pip !TOOL_ARGS! & exit /b !errorlevel! )
if "!tool!"=="pip3"    ( "!python_exe!" -m pip !TOOL_ARGS! & exit /b !errorlevel! )

echo Error: tool '!tool!' not found
exit /b 1

REM ============================================
REM List Pythons
REM ============================================
:list_pythons
echo Installed Pythons:
set "found=0"

REM Prefer the official py launcher; covers python.org, Store, PEP 514 runtimes
for /f "usebackq delims=" %%L in (`py --list-paths 2^>nul`) do (
    echo   %%L
    set "found=1"
)

if "!found!"=="1" goto :list_summary

REM Fallback: scan standard dirs when py is missing (PythonXY\python.exe)
if "!PYTHON_BASE_DIR!"=="" goto :list_none
for /d %%d in ("!PYTHON_BASE_DIR!\Python*") do (
    if exist "%%d\python.exe" (
        call :ver_from_dir "%%~nxd" pyver
        echo   !pyver! - %%d\python.exe
        set "found=1"
    )
)

:list_none
if "!found!"=="0" echo   None found

:list_summary
echo.
if not "!PTOOL_DEFAULT_VERSION!"=="" echo Default: !PTOOL_DEFAULT_VERSION!
exit /b 0

REM ============================================
REM Help
REM ============================================
:show_help
echo ptool - Python version manager for Windows
echo.
echo Usage:
echo   ptool ^<tool^> ^<version^> [args...]   Run a tool
echo   ptool list                          List Pythons
echo   ptool use ^<version^>                Set default version
echo   ptool current                       Show current version
echo   ptool home ^<version^>               Show install path
echo   ptool info ^<version^>               Show details
echo   ptool tools ^<version^>              List tools
echo   ptool run ^<version^> ^<file.py^>    Run a Python file
echo   ptool scan                          Scan Python paths
echo   ptool config                        Show config
echo   ptool install                       Full install
echo   ptool update                        Check and update
echo   ptool uninstall [-y]                Uninstall (-y silent)
echo   ptool shim                          Rebuild shims
echo   ptool help                          Show help

:cmd_use
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
call :resolve_py "%~2" use_exe
if not defined use_exe ( echo Error: Python %~2 not found & exit /b 1 )

findstr /v "PTOOL_DEFAULT_VERSION" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
REM Redirect before echo: the other order appends a trailing space.
>>"%CONFIG_FILE%.tmp" echo PTOOL_DEFAULT_VERSION="%~2"
move /y "%CONFIG_FILE%.tmp" "%CONFIG_FILE%" >nul
set "PTOOL_DEFAULT_VERSION=%~2"
echo Default version set: %~2
exit /b 0

REM ============================================
REM current
REM ============================================
:cmd_current
if "!PTOOL_DEFAULT_VERSION!"=="" ( echo No default version & exit /b 1 )
echo Default: !PTOOL_DEFAULT_VERSION!
call :resolve_py "!PTOOL_DEFAULT_VERSION!" cur_exe
if not defined cur_exe set "cur_exe=(未找到，请运行 ptool scan)"
echo Path: !cur_exe!
exit /b 0

REM ============================================
REM home
REM ============================================
:cmd_home
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
call :resolve_py "%~2" home_exe
if not defined home_exe ( echo Error: Python %~2 not found >&2 & exit /b 1 )
for %%f in ("!home_exe!") do set "home_dir=%%~dpf"
set "home_dir=!home_dir:~0,-1!"
echo !home_dir!
exit /b 0

REM ============================================
REM info
REM ============================================
:cmd_info
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
call :resolve_py "%~2" info_exe
if not defined info_exe ( echo Error: Python %~2 not found & exit /b 1 )
for %%f in ("!info_exe!") do set "info_dir=%%~dpf"
set "info_dir=!info_dir:~0,-1!"
echo === Python %~2 ===
echo Path: !info_exe!
echo.
"!info_exe!" --version 2>&1
echo.
echo Tools:
for %%f in ("!info_dir!\python*.exe" "!info_dir!\pip*.exe") do echo   %%~nxf
exit /b 0

REM ============================================
REM tools
REM ============================================
:cmd_tools
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
call :resolve_py "%~2" tools_exe
if not defined tools_exe ( echo Error: Python %~2 not found & exit /b 1 )
for %%f in ("!tools_exe!") do set "tools_dir=%%~dpf"
set "tools_dir=!tools_dir:~0,-1!"
echo Python %~2 tools:
for %%f in ("!tools_dir!\python*.exe" "!tools_dir!\pip*.exe") do echo   %%~nxf
exit /b 0

REM ============================================
REM run
REM ============================================
:cmd_run
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
if "%~3"=="" ( echo Error: specify a file & exit /b 1 )
call :resolve_py "%~2" run_exe
if not defined run_exe ( echo Error: Python %~2 not found & exit /b 1 )
if not exist "%~3" ( echo Error: file not found & exit /b 1 )
echo === Run (Python %~2) ===
"!run_exe!" "%~3"
exit /b !errorlevel!

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
if exist "%CONFIG_FILE%" ( type "%CONFIG_FILE%" ) else ( echo Not found, run: ptool scan )
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
REM 写安装目录需要管理员权限，非管理员时自动请求提权（弹 UAC）
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
for /f "usebackq delims=" %%v in (`powershell -NoProfile -Command "(Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/CK627/MyProject/ptool/VERSION').Content.Trim()"`) do set "REMOTE_VERSION=%%v"
if "!REMOTE_VERSION!"=="" for /f "usebackq delims=" %%v in (`curl -fsSL "https://raw.githubusercontent.com/CK627/MyProject/ptool/VERSION" 2^>nul`) do if not defined REMOTE_VERSION set "REMOTE_VERSION=%%v"
if "!REMOTE_VERSION!"=="" (
    echo Version read failed, falling back to git...
    goto :update_via_git
)

set "LOCAL_VERSION="
if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        if "%%a"=="PTOOL_VERSION" set "LOCAL_VERSION=%%~b"
    )
)
if defined LOCAL_VERSION set "LOCAL_VERSION=!LOCAL_VERSION:"=!"
if defined LOCAL_VERSION set "LOCAL_VERSION=!LOCAL_VERSION: =!"

if "!LOCAL_VERSION!"=="!REMOTE_VERSION!" (
    echo Already up to date ^(v!LOCAL_VERSION!^)
    exit /b 0
)

echo New version: v!LOCAL_VERSION! -> v!REMOTE_VERSION!

set "UPD_TMP=%TEMP%\ptool-update"
rmdir /s /q "%UPD_TMP%" 2>nul
mkdir "%UPD_TMP%"

echo Downloading update...
powershell -NoProfile -Command "Invoke-WebRequest -UseBasicParsing 'https://github.com/CK627/MyProject/archive/refs/heads/ptool.tar.gz' -OutFile '%UPD_TMP%\src.tar.gz'"
if not exist "%UPD_TMP%\src.tar.gz" curl -fsSL "https://github.com/CK627/MyProject/archive/refs/heads/ptool.tar.gz" -o "%UPD_TMP%\src.tar.gz"
if not exist "%UPD_TMP%\src.tar.gz" ( echo Download failed, fallback to git & goto :update_via_git )

tar -xzf "%UPD_TMP%\src.tar.gz" -C "%UPD_TMP%"
if !errorlevel! neq 0 ( echo Extract failed & exit /b 1 )

set "SRC=%UPD_TMP%\MyProject-ptool"

copy /y "!SRC!\bin\ptool.bat" "%BIN_DIR%\" >nul
if !errorlevel! neq 0 (
    echo Error: cannot write %BIN_DIR%
    echo Please run as administrator
    exit /b 1
)
if exist "!SRC!\installer\windows\install.bat" (
    copy /y "!SRC!\installer\windows\install.bat" "%MODULE_DIR%\install.bat" >nul
)
if not exist "%CONFIG_FILE%" copy "!SRC!\config\ptool.conf" "%CONFIG_DIR%\" >nul

findstr /v /b /c:"PTOOL_VERSION=" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
REM Redirect before echo: the other order appends a trailing space.
>>"%CONFIG_FILE%.tmp" echo PTOOL_VERSION="!REMOTE_VERSION!"
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

set "REPO_DIR=%USERPROFILE%\.devtools\ptool\repo"
set "FRESH_CLONE=0"

if not exist "!REPO_DIR!\.git" (
    echo First update, cloning repo...
    git clone --branch ptool --single-branch --depth 1 https://github.com/CK627/MyProject.git "!REPO_DIR!"
    if !errorlevel! neq 0 ( echo Clone failed & exit /b 1 )
    set "FRESH_CLONE=1"
)

set "REMOTE_VERSION="
if "!FRESH_CLONE!"=="1" (
    for /f "usebackq tokens=*" %%v in ("!REPO_DIR!\VERSION") do if not defined REMOTE_VERSION set "REMOTE_VERSION=%%v"
) else (
    echo Checking for updates...
    git -C "!REPO_DIR!" fetch origin ptool 2>nul
    if !errorlevel! neq 0 ( echo Fetch failed, check network & exit /b 1 )
    for /f "usebackq tokens=*" %%v in (`git -C "!REPO_DIR!" show origin/ptool:VERSION 2^>nul`) do if not defined REMOTE_VERSION set "REMOTE_VERSION=%%v"
)
if "!REMOTE_VERSION!"=="" ( echo Error: cannot get version & exit /b 1 )

set "LOCAL_VERSION="
if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        if "%%a"=="PTOOL_VERSION" set "LOCAL_VERSION=%%~b"
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
    git -C "!REPO_DIR!" checkout ptool 2>nul
    git -C "!REPO_DIR!" pull origin ptool
    if !errorlevel! neq 0 ( echo Pull failed & exit /b 1 )
)

copy /y "!REPO_DIR!\bin\ptool.bat" "%BIN_DIR%\" >nul
if !errorlevel! neq 0 (
    echo Error: cannot write %BIN_DIR%
    echo Please run as administrator
    exit /b 1
)
if exist "!REPO_DIR!\installer\windows\install.bat" (
    copy /y "!REPO_DIR!\installer\windows\install.bat" "%MODULE_DIR%\install.bat" >nul
)
if not exist "%CONFIG_FILE%" copy "!REPO_DIR!\config\ptool.conf" "%CONFIG_DIR%\" >nul

findstr /v /b /c:"PTOOL_VERSION=" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
REM Redirect before echo: the other order appends a trailing space.
>>"%CONFIG_FILE%.tmp" echo PTOOL_VERSION="!REMOTE_VERSION!"
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
set "SHIMS_DIR=%USERPROFILE%\.devtools\ptool\shims"
if not exist "!SHIMS_DIR!" mkdir "!SHIMS_DIR!"

REM shims are thin forwards; ptool resolves the interpreter path itself
REM so the path logic lives only in :resolve_py, never duplicated
REM The old code copied the logic into each shim and forgot setlocal
for %%t in (python python3 pip pip3) do (
    (
        echo @echo off
        echo REM ptool shim - auto generated
        echo set "CONFIG_FILE=!CONFIG_FILE!"
        echo for %%%%i in ^("%%CONFIG_FILE%%\..\.."^) do set "PTOOL_ROOT=%%%%~fi"
        echo if not exist "%%PTOOL_ROOT%%\bin\ptool.bat" ^(
        echo     echo ptool: %%PTOOL_ROOT%%\bin\ptool.bat not found ^>^&2
        echo     exit /b 1
        echo ^)
        echo "%%PTOOL_ROOT%%\bin\ptool.bat" %%t %%*
    ) > "!SHIMS_DIR!\%%t.bat"
)

echo Shims created: !SHIMS_DIR!

REM 确保 shims 目录在用户 PATH（否则 `python` 走系统 Python，不用默认版本）
powershell -NoProfile -Command "$d = Join-Path $env:USERPROFILE '.devtools\ptool\shims'; $p = [Environment]::GetEnvironmentVariable('Path','User'); $parts = @($p -split ';' | Where-Object { $_ -and ($_ -ne $d) }); [Environment]::SetEnvironmentVariable('Path', ($d + ';' + ($parts -join ';')).TrimEnd(';'), 'User'); Write-Output 'shims moved to front of user PATH'"
exit /b 0

REM ============================================
REM Resolve the interpreter path for a version
REM
REM Prefer the official py launcher to print the interpreter path
REM Covers python.org, Store, and any PEP 514 runtime
REM Fall back to scanning standard dirs when py is missing
REM
REM arg1 = version, e.g. 3.10
REM arg2 = variable to receive the result; empty if not found
REM ============================================
:resolve_py
set "%~2="
set "_RV=%~1"
if "!_RV!"=="" exit /b 1

REM Prefer py: py -X.Y -c prints the interpreter path
REM Covers python.org, Microsoft Store, and any PEP 514 runtime
REM No need to guess directory layouts
for /f "delims=" %%p in ('py -!_RV! -c "import sys; print(sys.executable)" 2^>nul') do set "%~2=%%p"
if defined %~2 exit /b 0

REM Fallback: scan standard install dirs when py is missing
set "_RVND=!_RV:.=!"
if exist "!PYTHON_BASE_DIR!\Python!_RVND!\python.exe" (
    set "%~2=!PYTHON_BASE_DIR!\Python!_RVND!\python.exe"
    exit /b 0
)
if exist "!PYTHON_BASE_DIR!\python!_RV!.exe" (
    set "%~2=!PYTHON_BASE_DIR!\python!_RV!.exe"
    exit /b 0
)
exit /b 1

REM ============================================
REM Derive version from dir name: Python310 to 3.10, Python27 to 2.7
REM arg1 = dir name, arg2 = variable to receive the version
REM ============================================
:ver_from_dir
set "%~2="
set "_VD=%~1"
REM Dir name is Python plus 1-digit major and 1-2 digit minor, split by position
REM   Python311 to 3.11, Python27 to 2.7, Python36 to 3.6, Python312 to 3.12
if "!_VD:~6,1!"=="" exit /b 0
set "%~2=!_VD:~6,1!.!_VD:~7,2!"
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
