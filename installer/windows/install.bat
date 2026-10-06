@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM jtool 安装脚本 (Windows)

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM 布局感知：
REM   仓库里本脚本在 <tool>\installer\windows\ ，往上两级才是项目根目录
REM   安装后本脚本在 <tool>\module\         ，往上一级就是安装根目录
REM 不区分的话，安装后 %PROJECT_DIR% 会算成 C:\Program Files\devtools，
REM 既找不到 bin\ 也找不到 VERSION，:write_version 会静默退出，
REM 于是每次 update 都误报有新版本。
for %%i in ("%SCRIPT_DIR%\..") do set "APP_ROOT=%%~fi"
for %%i in ("%SCRIPT_DIR%\..\..") do set "REPO_ROOT=%%~fi"
if exist "%APP_ROOT%\bin\jtool.bat" (
    set "PROJECT_DIR=%APP_ROOT%"
    set "INSTALLED=1"
) else (
    set "PROJECT_DIR=%REPO_ROOT%"
    set "INSTALLED=0"
)

REM 已在安装目录中时以实际位置为准；从仓库安装才用规范目标路径
if "%INSTALLED%"=="1" (
    set "INSTALL_DIR=%PROJECT_DIR%"
) else (
    set "INSTALL_DIR=C:\Program Files\devtools\jtool"
)
set "BIN_DIR=%INSTALL_DIR%\bin"
set "CONFIG_DIR=%INSTALL_DIR%\config"
set "MODULE_DIR=%INSTALL_DIR%\module"
set "CONFIG_FILE=%CONFIG_DIR%\jtool.conf"

REM ============================================
REM 子命令
REM ============================================
if "%~1"=="scan" goto :do_scan
if "%~1"=="config" goto :do_config
if "%~1"=="help" goto :do_help

REM ============================================
REM 完整安装
REM ============================================
echo ========================================
echo   jtool 安装程序 (Windows)
echo ========================================
echo.

echo [1/4] 复制文件...
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if not exist "%MODULE_DIR%" mkdir "%MODULE_DIR%"
if "%INSTALLED%"=="1" (
    echo 已处于安装布局，跳过文件复制
) else (
    copy "%PROJECT_DIR%\bin\jtool.bat" "%BIN_DIR%\" >nul
    if not exist "%CONFIG_FILE%" copy "%PROJECT_DIR%\config\jtool.conf" "%CONFIG_DIR%\" >nul
    REM 把本安装脚本复制到 module\ ，供 jtool install / jtool scan 调用
    copy "%PROJECT_DIR%\installer\windows\install.bat" "%MODULE_DIR%\install.bat" >nul
)
echo 完成
echo.

echo [2/4] 设置权限...
icacls "%INSTALL_DIR%" /grant Everyone:(OI)(CI)RX >nul 2>&1
icacls "%BIN_DIR%\jtool.bat" /grant Everyone:RX >nul 2>&1
echo 完成
echo.

echo [3/4] 扫描并生成 shim...
call :do_scan_inner
call :write_version
"%BIN_DIR%\jtool.bat" shim
echo.

echo [4/4] 配置 PATH...
powershell -NoProfile -Command "$p=[Environment]::GetEnvironmentVariable('Path','User'); $add=@('%BIN_DIR%','%USERPROFILE%\.devtools\jtool\shims'); $chg=$false; foreach($d in $add){ if(-not ((';'+$p+';') -like ('*;'+$d+';*'))){ $p=($d+';'+$p.TrimStart(';')); $chg=$true } }; if($chg){ [Environment]::SetEnvironmentVariable('Path',$p,'User') }; Write-Output '已添加到用户 PATH'"

echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo 安装目录: %INSTALL_DIR%
echo 配置文件: %CONFIG_FILE%
echo 请重新打开 CMD 窗口
echo.
pause
exit /b 0

REM ============================================
REM 扫描
REM ============================================
:do_scan
echo [扫描] 检测 Java 安装路径...
echo.

set "found_dir="
if exist "C:\Program Files\Java" (
    for /d %%d in ("C:\Program Files\Java\jdk-*") do (
        if exist "%%d\bin\java.exe" (
            set "found_dir=C:\Program Files\Java"
            goto :scan_found
        )
    )
)
if exist "C:\Program Files\Eclipse Adoptium" (
    set "found_dir=C:\Program Files\Eclipse Adoptium"
    goto :scan_found
)

echo 未找到 Java 安装目录
set /p "found_dir=请输入 Java 安装路径: "
if not exist "!found_dir!" (
    echo 错误: 路径不存在
    exit /b 1
)

:scan_found
echo 找到: !found_dir!
echo.
echo 已安装的 JDK:
for /d %%d in ("!found_dir!\jdk-*") do (
    if exist "%%d\bin\java.exe" (
        for /f "tokens=*" %%v in ('"%%d\bin\java.exe" -version 2^>^&1 ^| findstr /i "version"') do (
            echo   %%~nxd - %%v
        )
    )
)
echo.

call :write_config

echo 配置文件已写入: %CONFIG_FILE%
echo.
type "%CONFIG_FILE%"
exit /b 0

:do_scan_inner
set "found_dir="
if exist "C:\Program Files\Java" (
    for /d %%d in ("C:\Program Files\Java\jdk-*") do (
        if exist "%%d\bin\java.exe" (
            set "found_dir=C:\Program Files\Java"
            goto :scan_inner_found
        )
    )
)
if exist "C:\Program Files\Eclipse Adoptium" set "found_dir=C:\Program Files\Eclipse Adoptium"

:scan_inner_found
if not defined found_dir set "found_dir=C:\Program Files\Java"
call :write_config
echo 已写入: %CONFIG_FILE%
exit /b 0

REM ============================================
REM 写入配置文件（保留已有的默认版本与版本记录）
REM ============================================
:write_config
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if not defined found_dir set "found_dir=C:\Program Files\Java"

set "KEEP_DEFAULT=# JTOOL_DEFAULT_VERSION="21""
set "KEEP_VERSION=# JTOOL_VERSION="""
if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        if "%%a"=="JTOOL_DEFAULT_VERSION" set "KEEP_DEFAULT=%%a=%%b"
        if "%%a"=="JTOOL_VERSION" set "KEEP_VERSION=%%a=%%b"
    )
)

(
    echo # jtool 配置文件
    echo.
    echo # Java 安装路径（父目录）
    echo JAVA_BASE_DIR="!found_dir!"
    echo.
    echo # 默认版本
    echo !KEEP_DEFAULT!
    echo.
    echo # jtool 版本（由 install / update 维护，请勿手动修改）
    echo !KEEP_VERSION!
) > "%CONFIG_FILE%"
exit /b 0

REM ============================================
REM 记录 jtool 版本号
REM ============================================
:write_version
if not exist "%PROJECT_DIR%\VERSION" exit /b 0
set "VER="
for /f "usebackq tokens=*" %%v in ("%PROJECT_DIR%\VERSION") do if not defined VER set "VER=%%v"
if not defined VER exit /b 0
findstr /v /b /c:"JTOOL_VERSION=" "%CONFIG_FILE%" > "%CONFIG_FILE%.tmp"
echo JTOOL_VERSION="!VER!" >> "%CONFIG_FILE%.tmp"
move /y "%CONFIG_FILE%.tmp" "%CONFIG_FILE%" >nul
exit /b 0

REM ============================================
REM 查看配置
REM ============================================
:do_config
echo 配置文件: %CONFIG_FILE%
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
echo jtool 安装脚本 (Windows)
echo.
echo 用法:
echo   install.bat          完整安装
echo   install.bat scan     扫描 Java 路径，更新配置
echo   install.bat config   查看配置
echo   install.bat help     帮助
exit /b 0
