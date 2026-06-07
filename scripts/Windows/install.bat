@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ptool 安装脚本 (Windows)

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
REM 向上两级到项目根目录
for %%i in ("%SCRIPT_DIR%\..\..") do set "PROJECT_DIR=%%~fi"
set "INSTALL_DIR=C:\Program Files\devtools\ptool"
set "BIN_DIR=%INSTALL_DIR%\bin"
set "CONFIG_DIR=%INSTALL_DIR%\config"
set "MODULE_DIR=%INSTALL_DIR%\module"
set "CONFIG_FILE=%CONFIG_DIR%\ptool.conf"

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
echo   ptool 安装程序 (Windows)
echo ========================================
echo.

echo [1/4] 复制文件...
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if not exist "%MODULE_DIR%" mkdir "%MODULE_DIR%"
copy "%PROJECT_DIR%\bin\ptool.bat" "%BIN_DIR%\" >nul
copy "%PROJECT_DIR%\config\ptool.conf" "%CONFIG_DIR%\" >nul
copy "%PROJECT_DIR%\module\install.sh" "%MODULE_DIR%\" >nul
echo 完成
echo.

echo [2/4] 设置权限...
icacls "%INSTALL_DIR%" /grant Everyone:(OI)(CI)RX >nul 2>&1
icacls "%BIN_DIR%\ptool.bat" /grant Everyone:RX >nul 2>&1
echo 完成
echo.

echo [3/4] 扫描 Python...
call :do_scan_inner
echo.

echo [4/4] 配置 PATH...
echo %PATH% | findstr /i /c:"%BIN_DIR%" >nul
if !errorlevel! equ 0 (
    echo 已存在
) else (
    setx PATH "%PATH%;%BIN_DIR%" >nul 2>&1
    echo 已添加到 PATH
)

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
echo [扫描] 检测 Python 安装路径...
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

echo 未找到 Python 安装目录
set /p "found_dir=请输入 Python 安装路径: "
if not exist "!found_dir!" (
    echo 错误: 路径不存在
    exit /b 1
)

:scan_found
echo 找到: !found_dir!
echo.
echo 已安装的 Python:
for /d %%d in ("!found_dir!\Python*") do (
    if exist "%%d\python.exe" (
        for /f "tokens=*" %%v in ('"%%d\python.exe" --version 2^>^&1') do (
            echo   %%~nxd - %%v
        )
    )
)
echo.

if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
(
    echo # ptool 配置文件
    echo.
    echo # Python 安装路径（父目录）
    echo PYTHON_BASE_DIR="!found_dir!"
    echo.
    echo # 默认版本
    echo # PTOOL_DEFAULT_VERSION="3.11"
) > "%CONFIG_FILE%"

echo 配置文件已写入: %CONFIG_FILE%
echo.
type "%CONFIG_FILE%"
exit /b 0

:do_scan_inner
set "found_dir=C:\"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
(
    echo # ptool 配置文件
    echo.
    echo # Python 安装路径（父目录）
    echo PYTHON_BASE_DIR="!found_dir!"
    echo.
    echo # 默认版本
    echo # PTOOL_DEFAULT_VERSION="3.11"
) > "%CONFIG_FILE%"
echo 已写入: %CONFIG_FILE%
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
echo ptool 安装脚本 (Windows)
echo.
echo 用法:
echo   install.bat          完整安装
echo   install.bat scan     扫描 Python 路径，更新配置
echo   install.bat config   查看配置
echo   install.bat help     帮助
exit /b 0
