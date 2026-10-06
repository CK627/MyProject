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
if not exist "%INSTALL_MODULE%" set "INSTALL_MODULE=%PROJECT_DIR%\scripts\Windows\install.bat"
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

if "%~2"=="" (
    if not "!PTOOL_DEFAULT_VERSION!"=="" (
        set "version=!PTOOL_DEFAULT_VERSION!"
        goto :run_tool_no_shift
    ) else (
        echo 错误: 需要指定工具名和版本号
        exit /b 1
    )
)
set "version=%~2"
shift /1
shift /1
goto :run_tool

:run_tool_no_shift
shift /1
goto :run_tool

:run_tool
call :resolve_py "!version!" python_exe
if not defined python_exe (
    echo 错误: 找不到 Python !version!
    echo 基准目录: !PYTHON_BASE_DIR!
    echo 请运行 "ptool scan"，或修改配置里的 PYTHON_BASE_DIR
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

echo 错误: 工具 '!tool!' 不存在
exit /b 1

REM ============================================
REM List Pythons
REM ============================================
:list_pythons
echo 已安装的 Python:
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
if "!found!"=="0" echo   未找到

:list_summary
echo.
if not "!PTOOL_DEFAULT_VERSION!"=="" echo 默认版本: !PTOOL_DEFAULT_VERSION!
exit /b 0

REM ============================================
REM Help
REM ============================================
:show_help
echo ptool - 统一 Python 版本管理工具（Windows）
echo.
echo 用法:
echo   ptool ^<工具名^> ^<版本号^> [参数...]   运行工具
echo   ptool list                          列出 Python
echo   ptool use ^<版本号^>                  设置默认版本
echo   ptool current                       当前默认版本
echo   ptool home ^<版本号^>                 输出路径
echo   ptool info ^<版本号^>                 详细信息
echo   ptool tools ^<版本号^>                可用工具
echo   ptool run ^<版本号^> ^<python文件^>     运行文件
echo   ptool scan                          扫描路径
echo   ptool config                        显示配置
echo   ptool install                       完整安装
echo   ptool update                        检查并更新 ptool
echo   ptool uninstall [-y]                卸载（-y 静默）
echo   ptool shim                          重建 shim 脚本
echo   ptool help                          帮助
exit /b 0

REM ============================================
REM use
REM ============================================
:cmd_use
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
call :resolve_py "%~2" use_exe
if not defined use_exe ( echo 错误: Python %~2 不存在 & exit /b 1 )

findstr /v "PTOOL_DEFAULT_VERSION" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
echo PTOOL_DEFAULT_VERSION="%~2" >> "%CONFIG_FILE%.tmp"
move /y "%CONFIG_FILE%.tmp" "%CONFIG_FILE%" >nul
set "PTOOL_DEFAULT_VERSION=%~2"
echo 已设置默认版本: %~2
exit /b 0

REM ============================================
REM current
REM ============================================
:cmd_current
if "!PTOOL_DEFAULT_VERSION!"=="" ( echo 未设置默认版本 & exit /b 1 )
echo 默认版本: !PTOOL_DEFAULT_VERSION!
call :resolve_py "!PTOOL_DEFAULT_VERSION!" cur_exe
if not defined cur_exe set "cur_exe=(未找到，请运行 ptool scan)"
echo 路径: !cur_exe!
exit /b 0

REM ============================================
REM home
REM ============================================
:cmd_home
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
call :resolve_py "%~2" home_exe
if not defined home_exe ( echo 错误: Python %~2 不存在 >&2 & exit /b 1 )
for %%f in ("!home_exe!") do set "home_dir=%%~dpf"
set "home_dir=!home_dir:~0,-1!"
echo !home_dir!
exit /b 0

REM ============================================
REM info
REM ============================================
:cmd_info
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
call :resolve_py "%~2" info_exe
if not defined info_exe ( echo 错误: Python %~2 不存在 & exit /b 1 )
for %%f in ("!info_exe!") do set "info_dir=%%~dpf"
set "info_dir=!info_dir:~0,-1!"
echo === Python %~2 ===
echo 路径: !info_exe!
echo.
"!info_exe!" --version 2>&1
echo.
echo 工具:
for %%f in ("!info_dir!\python*.exe" "!info_dir!\pip*.exe") do echo   %%~nxf
exit /b 0

REM ============================================
REM tools
REM ============================================
:cmd_tools
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
call :resolve_py "%~2" tools_exe
if not defined tools_exe ( echo 错误: Python %~2 不存在 & exit /b 1 )
for %%f in ("!tools_exe!") do set "tools_dir=%%~dpf"
set "tools_dir=!tools_dir:~0,-1!"
echo Python %~2 工具:
for %%f in ("!tools_dir!\python*.exe" "!tools_dir!\pip*.exe") do echo   %%~nxf
exit /b 0

REM ============================================
REM run
REM ============================================
:cmd_run
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
if "%~3"=="" ( echo 错误: 请指定文件 & exit /b 1 )
call :resolve_py "%~2" run_exe
if not defined run_exe ( echo 错误: Python %~2 不存在 & exit /b 1 )
if not exist "%~3" ( echo 错误: 文件不存在 & exit /b 1 )
echo === 运行（Python %~2）===
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
echo 配置文件: %CONFIG_FILE%
echo.
if exist "%CONFIG_FILE%" ( type "%CONFIG_FILE%" ) else ( echo 不存在，请运行: ptool scan )
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
echo 正在检查更新...
set "REMOTE_VERSION="
for /f "usebackq delims=" %%v in (`curl -fsSL "https://raw.githubusercontent.com/CK627/MyProject/ptool/VERSION" 2^>nul`) do if not defined REMOTE_VERSION set "REMOTE_VERSION=%%v"
if "!REMOTE_VERSION!"=="" ( echo 错误: 无法获取版本号，请检查网络 & exit /b 1 )

set "LOCAL_VERSION="
if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        if "%%a"=="PTOOL_VERSION" set "LOCAL_VERSION=%%~b"
    )
)

if "!LOCAL_VERSION!"=="!REMOTE_VERSION!" (
    echo 已是最新版本 ^(v!LOCAL_VERSION!^)
    exit /b 0
)

echo 发现新版本: v!LOCAL_VERSION! → v!REMOTE_VERSION!

set "UPD_TMP=%TEMP%\ptool-update"
rmdir /s /q "%UPD_TMP%" 2>nul
mkdir "%UPD_TMP%"

echo 下载更新...
curl -fsSL "https://github.com/CK627/MyProject/archive/refs/heads/ptool.tar.gz" -o "%UPD_TMP%\src.tar.gz"
if !errorlevel! neq 0 ( echo 下载失败，请检查网络 & exit /b 1 )

tar -xzf "%UPD_TMP%\src.tar.gz" -C "%UPD_TMP%"
if !errorlevel! neq 0 ( echo 解压失败 & exit /b 1 )

set "SRC=%UPD_TMP%\MyProject-ptool"

copy /y "!SRC!\bin\ptool.bat" "%BIN_DIR%\" >nul
if !errorlevel! neq 0 (
    echo 错误: 无法写入 %BIN_DIR%
    echo 请以管理员身份重新运行
    exit /b 1
)
if exist "!SRC!\scripts\Windows\install.bat" (
    copy /y "!SRC!\scripts\Windows\install.bat" "%MODULE_DIR%\install.bat" >nul
)
if not exist "%CONFIG_FILE%" copy "!SRC!\config\ptool.conf" "%CONFIG_DIR%\" >nul

findstr /v /b /c:"PTOOL_VERSION=" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
echo PTOOL_VERSION="!REMOTE_VERSION!" >> "%CONFIG_FILE%.tmp"
move /y "%CONFIG_FILE%.tmp" "%CONFIG_FILE%" >nul

rmdir /s /q "%UPD_TMP%" 2>nul

echo 更新完成！
echo   版本: v!LOCAL_VERSION! → v!REMOTE_VERSION!
exit /b 0

REM ============================================
REM update via git (fallback)
REM ============================================
:update_via_git
where git >nul 2>&1
if !errorlevel! neq 0 (
    echo 错误: 未找到 git，且 curl/tar 也不可用，无法更新
    exit /b 1
)

set "REPO_DIR=%USERPROFILE%\.devtools\ptool\repo"
set "FRESH_CLONE=0"

if not exist "!REPO_DIR!\.git" (
    echo 首次更新，正在克隆仓库...
    git clone --branch ptool --single-branch --depth 1 https://github.com/CK627/MyProject.git "!REPO_DIR!"
    if !errorlevel! neq 0 ( echo 克隆失败 & exit /b 1 )
    set "FRESH_CLONE=1"
)

set "REMOTE_VERSION="
if "!FRESH_CLONE!"=="1" (
    for /f "usebackq tokens=*" %%v in ("!REPO_DIR!\VERSION") do if not defined REMOTE_VERSION set "REMOTE_VERSION=%%v"
) else (
    echo 正在检查更新...
    git -C "!REPO_DIR!" fetch origin ptool 2>nul
    if !errorlevel! neq 0 ( echo 获取更新失败，请检查网络 & exit /b 1 )
    for /f "usebackq tokens=*" %%v in (`git -C "!REPO_DIR!" show origin/ptool:VERSION 2^>nul`) do if not defined REMOTE_VERSION set "REMOTE_VERSION=%%v"
)
if "!REMOTE_VERSION!"=="" ( echo 错误: 无法获取版本号 & exit /b 1 )

set "LOCAL_VERSION="
if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        if "%%a"=="PTOOL_VERSION" set "LOCAL_VERSION=%%~b"
    )
)

if "!LOCAL_VERSION!"=="!REMOTE_VERSION!" (
    echo 已是最新版本 ^(v!LOCAL_VERSION!^)
    exit /b 0
)

echo 发现新版本: v!LOCAL_VERSION! → v!REMOTE_VERSION!

if "!FRESH_CLONE!"=="0" (
    git -C "!REPO_DIR!" checkout ptool 2>nul
    git -C "!REPO_DIR!" pull origin ptool
    if !errorlevel! neq 0 ( echo 拉取更新失败 & exit /b 1 )
)

copy /y "!REPO_DIR!\bin\ptool.bat" "%BIN_DIR%\" >nul
if !errorlevel! neq 0 (
    echo 错误: 无法写入 %BIN_DIR%
    echo 请以管理员身份重新运行
    exit /b 1
)
if exist "!REPO_DIR!\scripts\Windows\install.bat" (
    copy /y "!REPO_DIR!\scripts\Windows\install.bat" "%MODULE_DIR%\install.bat" >nul
)
if not exist "%CONFIG_FILE%" copy "!REPO_DIR!\config\ptool.conf" "%CONFIG_DIR%\" >nul

findstr /v /b /c:"PTOOL_VERSION=" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
echo PTOOL_VERSION="!REMOTE_VERSION!" >> "%CONFIG_FILE%.tmp"
move /y "%CONFIG_FILE%.tmp" "%CONFIG_FILE%" >nul

echo 更新完成！
echo   版本: v!LOCAL_VERSION! → v!REMOTE_VERSION!
exit /b 0

REM ============================================
REM uninstall
REM ============================================
:cmd_uninstall
if "%~2"=="-y" goto :uninstall_silent
if exist "%INSTALL_DIR%\unins000.exe" (
    start "" "%INSTALL_DIR%\unins000.exe"
    echo 已启动卸载程序，请在弹窗中确认
) else (
    echo 未找到卸载器 %INSTALL_DIR%\unins000.exe
    echo 请通过「控制面板 - 添加或删除程序」卸载
)
exit /b 0

:uninstall_silent
if exist "%INSTALL_DIR%\unins000.exe" (
    start /wait "" "%INSTALL_DIR%\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
    echo 卸载完成
) else (
    echo 未找到卸载器 %INSTALL_DIR%\unins000.exe
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
        echo     echo ptool: 找不到 %%PTOOL_ROOT%%\bin\ptool.bat ^>^&2
        echo     exit /b 1
        echo ^)
        echo "%%PTOOL_ROOT%%\bin\ptool.bat" %%t %%*
    ) > "!SHIMS_DIR!\%%t.bat"
)

echo Shim 已创建: !SHIMS_DIR!
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
