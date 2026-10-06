@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM jtool - 统一 Java 版本管理工具 (Windows)

REM ============================================
REM 路径
REM ============================================
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_DIR=%%~fi"
set "CONFIG_FILE=%PROJECT_DIR%\config\jtool.conf"

REM 安装路径由脚本自身位置推导，不再写死 C:\Program Files\devtools\jtool。
REM 安装包可能装到 Program Files 或 Program Files (x86)（取决于安装器的
REM 位数模式），写死会导致 update 往不存在的路径写。
set "INSTALL_DIR=%PROJECT_DIR%"
set "BIN_DIR=%INSTALL_DIR%\bin"
set "CONFIG_DIR=%INSTALL_DIR%\config"
set "MODULE_DIR=%INSTALL_DIR%\module"

REM 查找 install.bat：已安装布局 → 仓库布局 → 旧版根目录
set "INSTALL_MODULE=%PROJECT_DIR%\module\install.bat"
if not exist "%INSTALL_MODULE%" set "INSTALL_MODULE=%PROJECT_DIR%\installer\windows\install.bat"
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
if "%~1"=="uninstall" goto :cmd_uninstall
if "%~1"=="shim" goto :cmd_shim

REM 运行工具
set "tool=%~1"
if "!JAVA_BASE_DIR!"=="" (
    echo Error: JAVA_BASE_DIR not set
    echo Run: jtool scan
    exit /b 1
)

set "version=%~2"

REM 版本号总是数字开头；若第二个参数缺失、或以 - / 开头（是参数不是版本号），
REM 则用默认版本。shim 转发 `java -version` 就是「工具 + 参数、无版本号」的形式。
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
) else (
    echo Error: need tool name and version
    exit /b 1
)

:run_tool
if "!version!"=="8" set "version=1.8"
set "jdk_home=!JAVA_BASE_DIR!\jdk-!version!.jdk\Contents\Home"
set "tool_path=!jdk_home!\bin\!tool!"

if not exist "!tool_path!.exe" (
    if not exist "!tool_path!" (
        echo Error: JDK !version! has no !tool! tool
        exit /b 1
    )
)

REM %* 不随 shift 变化，会带上工具名和版本号，这里重新拼接剩余参数
set "TOOL_ARGS="
:collect_args
if "%~1"=="" goto :args_ready
set "TOOL_ARGS=!TOOL_ARGS! %1"
shift /1
goto :collect_args
:args_ready

!tool_path! !TOOL_ARGS!
exit /b !errorlevel!

REM ============================================
REM 列出 JDK
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
if "!found!"=="0" echo   None found
echo.
if not "!JTOOL_DEFAULT_VERSION!"=="" echo Default: !JTOOL_DEFAULT_VERSION!
exit /b 0

REM ============================================
REM 帮助
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

:cmd_use
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
set "use_ver=%~2"
if "!use_ver!"=="8" set "use_ver=1.8"
set "use_home=!JAVA_BASE_DIR!\jdk-!use_ver!.jdk\Contents\Home"
if not exist "!use_home!" ( echo Error: JDK %~2 not found & exit /b 1 )

REM 更新配置文件
findstr /v "JTOOL_DEFAULT_VERSION" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
echo JTOOL_DEFAULT_VERSION="%~2" >> "%CONFIG_FILE%.tmp"
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
set "cur_ver=!JTOOL_DEFAULT_VERSION!"
if "!cur_ver!"=="8" set "cur_ver=1.8"
echo Default: !JTOOL_DEFAULT_VERSION!
echo JAVA_HOME: !JAVA_BASE_DIR!\jdk-!cur_ver!.jdk\Contents\Home
exit /b 0

REM ============================================
REM home
REM ============================================
:cmd_home
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
set "home_ver=%~2"
if "!home_ver!"=="8" set "home_ver=1.8"
set "home_path=!JAVA_BASE_DIR!\jdk-!home_ver!.jdk\Contents\Home"
if not exist "!home_path!" ( echo Error: JDK %~2 not found & exit /b 1 )
echo !home_path!
exit /b 0

REM ============================================
REM info
REM ============================================
:cmd_info
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
set "info_ver=%~2"
if "!info_ver!"=="8" set "info_ver=1.8"
set "info_home=!JAVA_BASE_DIR!\jdk-!info_ver!.jdk\Contents\Home"
if not exist "!info_home!" ( echo Error: JDK %~2 not found & exit /b 1 )
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
set "tools_ver=%~2"
if "!tools_ver!"=="8" set "tools_ver=1.8"
set "tools_home=!JAVA_BASE_DIR!\jdk-!tools_ver!.jdk\Contents\Home"
if not exist "!tools_home!" ( echo Error: JDK %~2 not found & exit /b 1 )
echo JDK %~2 tools:
for %%f in ("!tools_home!\bin\*") do echo   %%~nxf
exit /b 0

REM ============================================
REM run
REM ============================================
:cmd_run
if "%~2"=="" ( echo Error: specify a version & exit /b 1 )
if "%~3"=="" ( echo Error: specify a file & exit /b 1 )
set "run_ver=%~2"
set "java_file=%~3"
if not exist "!java_file!" ( echo Error: file not found & exit /b 1 )
if "!run_ver!"=="8" set "run_ver=1.8"
set "run_home=!JAVA_BASE_DIR!\jdk-!run_ver!.jdk\Contents\Home"
if not exist "!run_home!" ( echo Error: JDK %~2 not found & exit /b 1 )

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
echo JTOOL_VERSION="!REMOTE_VERSION!" >> "%CONFIG_FILE%.tmp"
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
echo JTOOL_VERSION="!REMOTE_VERSION!" >> "%CONFIG_FILE%.tmp"
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
        echo     echo jtool: no default version, run jtool use ^<version^>
        echo     exit /b 1
        echo ^)
        echo set "VER=!JTOOL_DEFAULT_VERSION!"
        echo if "!VER!"=="8" set "VER=1.8"
        echo set "JDK_HOME=!JAVA_BASE_DIR!\jdk-!VER!.jdk\Contents\Home"
        echo if not exist "!JDK_HOME!\bin\%%t.exe" ^(
        echo     echo jtool: JDK !JTOOL_DEFAULT_VERSION! has no %%t
        echo     exit /b 1
        echo ^)
        echo "!JDK_HOME!\bin\%%t.exe" %%*
    ) > "!SHIMS_DIR!\%%t.bat"
)

echo Shims created: !SHIMS_DIR!

REM 确保 shims 目录在用户 PATH（否则 `java` 走系统 Java，不用默认版本）
powershell -NoProfile -Command "$d = Join-Path $env:USERPROFILE '.devtools\jtool\shims'; $p = [Environment]::GetEnvironmentVariable('Path','User'); $parts = @($p -split ';' | Where-Object { $_ -and ($_ -ne $d) }); [Environment]::SetEnvironmentVariable('Path', ($d + ';' + ($parts -join ';')).TrimEnd(';'), 'User'); Write-Output 'shims moved to front of user PATH'"
exit /b 0
