@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM jtool - 统一 Java 版本管理工具 (Windows)

REM ============================================
REM 路径
REM ============================================
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "PROJECT_DIR=%SCRIPT_DIR%\.."
set "CONFIG_FILE=%PROJECT_DIR%\config\jtool.conf"

REM 查找 install.bat（优先 module/，回退根目录）
set "INSTALL_MODULE=%PROJECT_DIR%\module\install.bat"
if not exist "%INSTALL_MODULE%" set "INSTALL_MODULE=%PROJECT_DIR%\install.bat"

REM ============================================
REM 加载配置
REM ============================================
set "JAVA_BASE_DIR="
set "JTOOL_DEFAULT_VERSION="

if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        set "key=%%a"
        set "val=%%b"
        if not "!key:~0,1!"=="#" if not "!key!"=="" (
            set "val=!val:"=!"
            if "!key!"=="JAVA_BASE_DIR" set "JAVA_BASE_DIR=!val!"
            if "!key!"=="JTOOL_DEFAULT_VERSION" set "JTOOL_DEFAULT_VERSION=!val!"
        )
    )
)

REM ============================================
REM 主逻辑
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
if "%~1"=="shim" goto :cmd_shim

REM 运行工具
set "tool=%~1"
if "!JAVA_BASE_DIR!"=="" (
    echo 错误: 未配置 JAVA_BASE_DIR
    echo 请运行: jtool scan
    exit /b 1
)

if "%~2"=="" (
    if not "!JTOOL_DEFAULT_VERSION!"=="" (
        set "version=!JTOOL_DEFAULT_VERSION!"
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
if "!version!"=="8" set "version=1.8"
set "jdk_home=!JAVA_BASE_DIR!\jdk-!version!.jdk\Contents\Home"
set "tool_path=!jdk_home!\bin\!tool!"

if not exist "!tool_path!.exe" (
    if not exist "!tool_path!" (
        echo 错误: JDK !version! 没有 !tool! 工具
        exit /b 1
    )
)

!tool_path! %*
exit /b !errorlevel!

REM ============================================
REM 列出 JDK
REM ============================================
:list_jdks
if "!JAVA_BASE_DIR!"=="" (
    echo 错误: 未配置 JAVA_BASE_DIR
    echo 请运行: jtool scan
    exit /b 1
)

echo Java 路径: !JAVA_BASE_DIR!
echo.
echo 已安装的 JDK:
set "found=0"
for /d %%d in ("!JAVA_BASE_DIR!\jdk-*") do (
    if exist "%%d\Contents\Home\bin\java.exe" (
        set "dirname=%%~nxd"
        set "ver=!dirname:jdk-=!"
        set "ver=!ver:.jdk=!"
        for /f "tokens=*" %%v in ('"%%d\Contents\Home\bin\java.exe" -version 2^>^&1 ^| findstr /i "version"') do (
            echo   !ver! - %%v
            set "found=1"
        )
    )
    if exist "%%d\bin\java.exe" (
        set "dirname=%%~nxd"
        set "ver=!dirname:jdk-=!"
        for /f "tokens=*" %%v in ('"%%d\bin\java.exe" -version 2^>^&1 ^| findstr /i "version"') do (
            echo   !ver! - %%v
            set "found=1"
        )
    )
)
if "!found!"=="0" echo   (未找到)
echo.
if not "!JTOOL_DEFAULT_VERSION!"=="" echo 默认版本: !JTOOL_DEFAULT_VERSION!
exit /b 0

REM ============================================
REM 帮助
REM ============================================
:show_help
echo jtool - 统一 Java 版本管理工具 (Windows)
echo.
echo 用法:
echo   jtool ^<工具名^> ^<版本号^> [参数...]   运行工具
echo   jtool list                          列出 JDK
echo   jtool use ^<版本号^>                  设置默认版本
echo   jtool current                       当前默认版本
echo   jtool home ^<版本号^>                 输出 JAVA_HOME
echo   jtool info ^<版本号^>                 详细信息
echo   jtool tools ^<版本号^>                可用工具
echo   jtool run ^<版本号^> ^<java文件^>       编译并运行
echo   jtool scan                          扫描 Java 路径
echo   jtool config                        显示配置
echo   jtool install                       完整安装
echo   jtool update                        检查并更新 jtool
echo   jtool shim                          重建 shim 脚本
echo   jtool help                          帮助
exit /b 0

REM ============================================
REM use
REM ============================================
:cmd_use
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
set "use_ver=%~2"
if "!use_ver!"=="8" set "use_ver=1.8"
set "use_home=!JAVA_BASE_DIR!\jdk-!use_ver!.jdk\Contents\Home"
if not exist "!use_home!" ( echo 错误: JDK %~2 不存在 & exit /b 1 )

REM 更新配置文件
findstr /v "JTOOL_DEFAULT_VERSION" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
echo JTOOL_DEFAULT_VERSION="%~2" >> "%CONFIG_FILE%.tmp"
move /y "%CONFIG_FILE%.tmp" "%CONFIG_FILE%" >nul
set "JTOOL_DEFAULT_VERSION=%~2"
echo 已设置默认版本: %~2
echo JAVA_HOME: !use_home!
exit /b 0

REM ============================================
REM current
REM ============================================
:cmd_current
if "!JTOOL_DEFAULT_VERSION!"=="" ( echo 未设置默认版本 & exit /b 1 )
set "cur_ver=!JTOOL_DEFAULT_VERSION!"
if "!cur_ver!"=="8" set "cur_ver=1.8"
echo 默认版本: !JTOOL_DEFAULT_VERSION!
echo JAVA_HOME: !JAVA_BASE_DIR!\jdk-!cur_ver!.jdk\Contents\Home
exit /b 0

REM ============================================
REM home
REM ============================================
:cmd_home
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
set "home_ver=%~2"
if "!home_ver!"=="8" set "home_ver=1.8"
set "home_path=!JAVA_BASE_DIR!\jdk-!home_ver!.jdk\Contents\Home"
if not exist "!home_path!" ( echo 错误: JDK %~2 不存在 & exit /b 1 )
echo !home_path!
exit /b 0

REM ============================================
REM info
REM ============================================
:cmd_info
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
set "info_ver=%~2"
if "!info_ver!"=="8" set "info_ver=1.8"
set "info_home=!JAVA_BASE_DIR!\jdk-!info_ver!.jdk\Contents\Home"
if not exist "!info_home!" ( echo 错误: JDK %~2 不存在 & exit /b 1 )
echo === JDK %~2 ===
echo JAVA_HOME: !info_home!
echo.
"!info_home!\bin\java.exe" -version 2>&1
echo.
echo 工具:
for %%f in ("!info_home!\bin\*") do echo   %%~nxf
exit /b 0

REM ============================================
REM tools
REM ============================================
:cmd_tools
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
set "tools_ver=%~2"
if "!tools_ver!"=="8" set "tools_ver=1.8"
set "tools_home=!JAVA_BASE_DIR!\jdk-!tools_ver!.jdk\Contents\Home"
if not exist "!tools_home!" ( echo 错误: JDK %~2 不存在 & exit /b 1 )
echo JDK %~2 工具:
for %%f in ("!tools_home!\bin\*") do echo   %%~nxf
exit /b 0

REM ============================================
REM run
REM ============================================
:cmd_run
if "%~2"=="" ( echo 错误: 请指定版本号 & exit /b 1 )
if "%~3"=="" ( echo 错误: 请指定文件 & exit /b 1 )
set "run_ver=%~2"
set "java_file=%~3"
if not exist "!java_file!" ( echo 错误: 文件不存在 & exit /b 1 )
if "!run_ver!"=="8" set "run_ver=1.8"
set "run_home=!JAVA_BASE_DIR!\jdk-!run_ver!.jdk\Contents\Home"
if not exist "!run_home!" ( echo 错误: JDK %~2 不存在 & exit /b 1 )

for %%f in ("!java_file!") do set "class_name=%%~nf"
echo === 编译 (JDK %~2) ===
"!run_home!\bin\javac.exe" "!java_file!"
if !errorlevel! neq 0 ( echo 编译失败 & exit /b 1 )
echo.
echo === 运行 ===
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
echo 配置文件: %CONFIG_FILE%
echo.
if exist "%CONFIG_FILE%" ( type "%CONFIG_FILE%" ) else ( echo (不存在，请运行: jtool scan) )
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

set "REPO_DIR=%USERPROFILE%\.devtools\jtool\repo"

if not exist "!REPO_DIR!\.git" (
    echo 首次更新，正在克隆仓库...
    git clone --branch jtool --single-branch https://github.com/CK627/MyProject.git "!REPO_DIR!"
    if !errorlevel! neq 0 ( echo 克隆失败 & exit /b 1 )
)

echo 正在检查更新...
git -C "!REPO_DIR!" fetch origin jtool 2>nul
if !errorlevel! neq 0 ( echo 获取更新失败，请检查网络 & exit /b 1 )

for /f %%a in ('git -C "!REPO_DIR!" rev-parse HEAD') do set "LOCAL_SHA=%%a"
for /f %%a in ('git -C "!REPO_DIR!" rev-parse origin/jtool') do set "REMOTE_SHA=%%a"

if "!LOCAL_SHA!"=="!REMOTE_SHA!" (
    echo 已是最新版本
    exit /b 0
)

git -C "!REPO_DIR!" checkout jtool 2>nul
git -C "!REPO_DIR!" pull origin jtool
if !errorlevel! neq 0 ( echo 拉取更新失败 & exit /b 1 )

copy /y "!REPO_DIR!\bin\jtool.bat" "%BIN_DIR%\" >nul
copy /y "!REPO_DIR!\module\install.sh" "%MODULE_DIR%\" >nul
if not exist "%CONFIG_FILE%" copy "!REPO_DIR!\config\jtool.conf" "%CONFIG_DIR%\" >nul

echo 更新完成！
echo   旧版本: !LOCAL_SHA:~0,7!
echo   新版本: !REMOTE_SHA:~0,7!
exit /b 0

REM ============================================
REM shim
REM ============================================
:cmd_shim
set "SHIMS_DIR=%USERPROFILE%\.devtools\jtool\shims"
if not exist "!SHIMS_DIR!" mkdir "!SHIMS_DIR!"

for %%t in (java javac jar jshell javadoc javap) do (
    (
        echo @echo off
        echo REM jtool shim - auto generated
        echo set "CONFIG_FILE=%CONFIG_FILE%"
        echo set "JAVA_BASE_DIR="
        echo set "JTOOL_DEFAULT_VERSION="
        echo if exist "%%CONFIG_FILE%%" ^(
        echo     for /f "usebackq tokens=1,* delims==" %%%%a in ^("%%CONFIG_FILE%%"^) do ^(
        echo         set "key=%%%%a"
        echo         set "val=%%%%b"
        echo         if not "!key:~0,1!"=="#" if not "!key!"=="" ^(
        echo             set "val=!val:"=!"
        echo             if "!key!"=="JAVA_BASE_DIR" set "JAVA_BASE_DIR=!val!"
        echo             if "!key!"=="JTOOL_DEFAULT_VERSION" set "JTOOL_DEFAULT_VERSION=!val!"
        echo         ^)
        echo     ^)
        echo ^)
        echo if "!JTOOL_DEFAULT_VERSION!"=="" ^(
        echo     echo jtool: 未设置默认版本，请运行 jtool use ^<版本号^>
        echo     exit /b 1
        echo ^)
        echo set "VER=!JTOOL_DEFAULT_VERSION!"
        echo if "!VER!"=="8" set "VER=1.8"
        echo set "JDK_HOME=!JAVA_BASE_DIR!\jdk-!VER!.jdk\Contents\Home"
        echo if not exist "!JDK_HOME!\bin\%%t.exe" ^(
        echo     echo jtool: JDK !JTOOL_DEFAULT_VERSION! 没有 %%t
        echo     exit /b 1
        echo ^)
        echo "!JDK_HOME!\bin\%%t.exe" %%*
    ) > "!SHIMS_DIR!\%%t.bat"
)

echo Shim 已创建: !SHIMS_DIR!
exit /b 0
