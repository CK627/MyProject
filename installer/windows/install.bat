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
if "%INSTALLED%"=="1" (
    echo Installed layout, skip copying
) else (
    copy "%PROJECT_DIR%\bin\jtool.bat" "%BIN_DIR%\" >nul
    if not exist "%CONFIG_FILE%" copy "%PROJECT_DIR%\config\jtool.conf" "%CONFIG_DIR%\" >nul
    REM Copy this installer into module\ so jtool install / jtool scan can call it
    copy "%PROJECT_DIR%\installer\windows\install.bat" "%MODULE_DIR%\install.bat" >nul
)
echo Done
echo.

echo [2/4] Setting permissions...
icacls "%INSTALL_DIR%" /grant Everyone:(OI)(CI)RX >nul 2>&1
icacls "%BIN_DIR%\jtool.bat" /grant Everyone:RX >nul 2>&1
echo Done
echo.

echo [3/4] Scanning and generating shims...
call :do_scan_inner
call :write_version
"%BIN_DIR%\jtool.bat" shim
echo.

echo [4/4] Configuring PATH...
powershell -NoProfile -Command "$p=[Environment]::GetEnvironmentVariable('Path','User'); $add=@('%BIN_DIR%','%USERPROFILE%\.devtools\jtool\shims'); $chg=$false; foreach($d in $add){ if(-not ((';'+$p+';') -like ('*;'+$d+';*'))){ $p=($d+';'+$p.TrimStart(';')); $chg=$true } }; if($chg){ [Environment]::SetEnvironmentVariable('Path',$p,'User') }; Write-Output 'added to user PATH'"

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

set "found_dir="
if exist "C:\Program Files\Java" (
    for /d %%d in ("C:\Program Files\Java\jdk*") do (
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

echo Java dir not found
set /p "found_dir=Enter Java install path: "
if not exist "!found_dir!" (
    echo Error: path does not exist
    exit /b 1
)

:scan_found
echo Found: !found_dir!
echo.
echo Installed JDKs:
for /d %%d in ("!found_dir!\jdk*") do (
    if exist "%%d\bin\java.exe" (
        for /f "tokens=*" %%v in ('"%%d\bin\java.exe" -version 2^>^&1 ^| findstr /i version') do (
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
if exist "C:\Program Files\Java" (
    for /d %%d in ("C:\Program Files\Java\jdk*") do (
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
echo Written: %CONFIG_FILE%
exit /b 0

REM ============================================
REM Write config (preserve existing default version)
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
REM Record jtool version
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
REM Non-interactive scan, for the installer package in silent mode
REM Reuses :do_scan_inner, which falls back to a default instead of
REM prompting the way :do_scan does
REM ============================================
:do_scan_silent
call :do_scan_inner
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
