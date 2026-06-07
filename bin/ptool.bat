@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ptool - 统一 Python 版本管理工具 (Windows)

REM ============================================
REM 路径
REM ============================================
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "PROJECT_DIR=%SCRIPT_DIR%\.."
set "CONFIG_FILE=%PROJECT_DIR%\config\ptool.conf"

REM 查找 install.bat（优先 module/，回退根目录）
set "INSTALL_MODULE=%PROJECT_DIR%\module\install.bat"
if not exist "%INSTALL_MODULE%" set "INSTALL_MODULE=%PROJECT_DIR%\install.bat"

REM ============================================
REM 加载配置
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
REM 主逻辑
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
if "%~1"=="shim" goto :cmd_shim

REM 运行工具
set "tool=%~1"
if "!PYTHON_BASE_DIR!"=="" (
    echo 错误: 未配置 PYTHON_BASE_DIR
    echo 请运行: ptool scan
    exit /b 1
)

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
set "python_path=!PYTHON_BASE_DIR!\python!version!"
set "tool_path=!PYTHON_BASE_DIR!\!tool!"

if "!tool!"=="python" (
    if exist "!python_path!.exe" ( "!python_path!.exe" %* & exit /b !errorlevel! )
    if exist "!python_path!" ( "!python_path!" %* & exit /b !errorlevel! )
)
if "!tool!"=="python3" (
    if exist "!python_path!.exe" ( "!python_path!.exe" %* & exit /b !errorlevel! )
)
if "!tool!"=="pip" (
    "!python_path!" -m pip %*
    exit /b !errorlevel!
)
if "!tool!"=="pip3" (
    "!python_path!" -m pip %*
    exit /b !errorlevel!
)

echo 错误: 工具 '!tool!' 不存在
exit /b 1

REM ============================================
REM 列出 Python
REM ============================================
:list_pythons
if "!PYTHON_BASE_DIR!"=="" (
    echo 错误: 未配置 PYTHON_BASE_DIR
    echo 请运行: ptool scan
    exit /b 1
)

echo Python 路径: !PYTHON_BASE_DIR!
echo.
echo 已安装的 Python:
set "found=0"
for %%f in ("!PYTHON_BASE_DIR!\python*.exe") do (
    for /f "tokens=*" %%v in ('"%%f" --version 2^>^&1') do (
        echo   %%~nf - %%v
        set "found=1"
    )
)
if "!found!"=="0" echo   (未找到)
echo.
if not "!PTOOL_DEFAULT_VERSION!"=="" echo 默认版本: !PTOOL_DEFAULT_VERSION!
exit /b 0

REM ============================================
REM 帮助
REM ============================================
:show_help
echo ptool - 统一 Python 版本管理工具 (Windows)
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
echo   ptool shim                          重建 shim 脚本
echo   ptool help                          帮助
exit /b 0

REM ============================================
REM use
REM ============================================
:cmd_use
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
set "use_path=!PYTHON_BASE_DIR!\python%~2"
if not exist "!use_path!.exe" ( echo 错误: Python %~2 不存在 & exit /b 1 )

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
echo 路径: !PYTHON_BASE_DIR!\python!PTOOL_DEFAULT_VERSION!
exit /b 0

REM ============================================
REM home
REM ============================================
:cmd_home
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
echo !PYTHON_BASE_DIR!
exit /b 0

REM ============================================
REM info
REM ============================================
:cmd_info
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
set "info_path=!PYTHON_BASE_DIR!\python%~2"
if not exist "!info_path!.exe" ( echo 错误: Python %~2 不存在 & exit /b 1 )
echo === Python %~2 ===
echo 路径: !info_path!.exe
echo.
"!info_path!.exe" --version 2>&1
echo.
echo 工具:
for %%f in ("!PYTHON_BASE_DIR!\python*%~2*") do echo   %%~nxf
for %%f in ("!PYTHON_BASE_DIR!\pip*%~2*") do echo   %%~nxf
exit /b 0

REM ============================================
REM tools
REM ============================================
:cmd_tools
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
echo Python %~2 工具:
for %%f in ("!PYTHON_BASE_DIR!\python*%~2*") do echo   %%~nxf
for %%f in ("!PYTHON_BASE_DIR!\pip*%~2*") do echo   %%~nxf
exit /b 0

REM ============================================
REM run
REM ============================================
:cmd_run
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
if "%~3"=="" ( echo 错误: 请指定文件 & exit /b 1 )
set "run_path=!PYTHON_BASE_DIR!\python%~2"
if not exist "!run_path!.exe" ( echo 错误: Python %~2 不存在 & exit /b 1 )
if not exist "%~3" ( echo 错误: 文件不存在 & exit /b 1 )
echo === 运行 (Python %~2) ===
"!run_path!.exe" "%~3"
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
if exist "%CONFIG_FILE%" ( type "%CONFIG_FILE%" ) else ( echo (不存在，请运行: ptool scan) )
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
where git >nul 2>&1
if !errorlevel! neq 0 (
    echo 错误: 未找到 git 命令，请先安装 Git for Windows
    echo 下载地址: https://git-scm.com/download/win
    exit /b 1
)

set "REPO_DIR=%USERPROFILE%\.ptool\repo"

if not exist "!REPO_DIR!\.git" (
    echo 首次更新，正在克隆仓库...
    git clone --branch ptool --single-branch https://github.com/CK627/MyProject.git "!REPO_DIR!"
    if !errorlevel! neq 0 ( echo 克隆失败 & exit /b 1 )
)

echo 正在检查更新...
git -C "!REPO_DIR!" fetch origin ptool 2>nul
if !errorlevel! neq 0 ( echo 获取更新失败，请检查网络 & exit /b 1 )

for /f %%a in ('git -C "!REPO_DIR!" rev-parse HEAD') do set "LOCAL_SHA=%%a"
for /f %%a in ('git -C "!REPO_DIR!" rev-parse origin/ptool') do set "REMOTE_SHA=%%a"

if "!LOCAL_SHA!"=="!REMOTE_SHA!" (
    echo 已是最新版本
    exit /b 0
)

git -C "!REPO_DIR!" checkout ptool 2>nul
git -C "!REPO_DIR!" pull origin ptool
if !errorlevel! neq 0 ( echo 拉取更新失败 & exit /b 1 )

copy /y "!REPO_DIR!\bin\ptool.bat" "%BIN_DIR%\" >nul
copy /y "!REPO_DIR!\module\install.sh" "%MODULE_DIR%\" >nul
if not exist "%CONFIG_FILE%" copy "!REPO_DIR!\config\ptool.conf" "%CONFIG_DIR%\" >nul

echo 更新完成！
echo   旧版本: !LOCAL_SHA:~0,7!
echo   新版本: !REMOTE_SHA:~0,7!
exit /b 0

REM ============================================
REM shim
REM ============================================
:cmd_shim
set "SHIMS_DIR=%USERPROFILE%\.ptool\shims"
if not exist "!SHIMS_DIR!" mkdir "!SHIMS_DIR!"

for %%t in (python python3 pip pip3) do (
    (
        echo @echo off
        echo REM ptool shim - auto generated
        echo set "CONFIG_FILE=%CONFIG_FILE%"
        echo set "PYTHON_BASE_DIR="
        echo set "PTOOL_DEFAULT_VERSION="
        echo if exist "%%CONFIG_FILE%%" ^(
        echo     for /f "usebackq tokens=1,* delims==" %%%%a in ^("%%CONFIG_FILE%%"^) do ^(
        echo         set "key=%%%%a"
        echo         set "val=%%%%b"
        echo         if not "!key:~0,1!"=="#" if not "!key!"=="" ^(
        echo             set "val=!val:"=!"
        echo             if "!key!"=="PYTHON_BASE_DIR" set "PYTHON_BASE_DIR=!val!"
        echo             if "!key!"=="PTOOL_DEFAULT_VERSION" set "PTOOL_DEFAULT_VERSION=!val!"
        echo         ^)
        echo     ^)
        echo ^)
        echo if "!PTOOL_DEFAULT_VERSION!"=="" ^(
        echo     echo ptool: 未设置默认版本，请运行 ptool use ^<版本号^>
        echo     exit /b 1
        echo ^)
        echo set "BIN=!PYTHON_BASE_DIR!\%%t!PTOOL_DEFAULT_VERSION!.exe"
        echo if not exist "!BIN!" ^(
        echo     echo ptool: !BIN! 不存在
        echo     exit /b 1
        echo ^)
        echo "!BIN!" %%*
    ) > "!SHIMS_DIR!\%%t.bat"
)

echo Shim 已创建: !SHIMS_DIR!
exit /b 0
