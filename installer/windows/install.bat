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
icacls "%INSTALL_DIR%" /grant Everyone:(OI)(CI)RX >nul 2>&1
icacls "%BIN_DIR%\ptool.bat" /grant Everyone:RX >nul 2>&1
echo Done
echo.

echo [3/4] Scanning and generating shims...
call :do_scan_inner
call :write_version
REM Generate shims
"%BIN_DIR%\ptool.bat" shim
echo.

echo [4/4] Configuring PATH...
REM Prepend bin and shims to user PATH via PowerShell (setx truncates at 1024)
powershell -NoProfile -Command "$p=[Environment]::GetEnvironmentVariable('Path','User'); $add=@('%BIN_DIR%','%USERPROFILE%\.devtools\ptool\shims'); $chg=$false; foreach($d in $add){ if(-not ((';'+$p+';') -like ('*;'+$d+';*'))){ $p=($d+';'+$p.TrimStart(';')); $chg=$true } }; if($chg){ [Environment]::SetEnvironmentVariable('Path',$p,'User') }; Write-Output '已添加到用户 PATH'"


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

set "KEEP_DEFAULT=# PTOOL_DEFAULT_VERSION="3.11""
set "KEEP_VERSION=# PTOOL_VERSION="""
if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        if "%%a"=="PTOOL_DEFAULT_VERSION" set "KEEP_DEFAULT=%%a=%%b"
        if "%%a"=="PTOOL_VERSION" set "KEEP_VERSION=%%a=%%b"
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
