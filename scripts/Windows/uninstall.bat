@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ptool 卸载脚本 (Windows)

echo ========================================
echo   ptool 卸载程序 (Windows)
echo ========================================
echo.

set /p "confirm=确定要卸载 ptool 吗？(y/n): "
if /i not "!confirm!"=="y" (
    echo 已取消
    pause
    exit /b 0
)

echo.

REM 删除安装目录
set "INSTALL_DIR=C:\Program Files\devtools\ptool"
if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%"
    echo [完成] 已删除 %INSTALL_DIR%
) else (
    echo [跳过] 安装目录不存在
)

echo.

REM 删除配置文件
set "CONFIG_FILE=%USERPROFILE%\.ptool.conf"
if exist "%CONFIG_FILE%" (
    set /p "keep_config=是否保留配置文件？(y/n): "
    if /i "!keep_config!"=="y" (
        echo [跳过] 保留配置文件 %CONFIG_FILE%
    ) else (
        del "%CONFIG_FILE%"
        echo [完成] 已删除 %CONFIG_FILE%
    )
) else (
    echo [跳过] 配置文件不存在
)

echo.

REM 清理环境变量
echo [环境] 清理 PATH...
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do (
    set "user_path=%%b"
    if defined user_path (
        set "user_path=!user_path:;%INSTALL_DIR%\bin=!"
        set "user_path=!user_path:%INSTALL_DIR%\bin;=!"
        set "user_path=!user_path:%INSTALL_DIR%\bin=!"
        reg add "HKCU\Environment" /v Path /t REG_EXPAND_SZ /d "!user_path!" /f >nul 2>&1
        echo [完成] 已从用户 PATH 中移除
    )
)

echo.
echo ========================================
echo   卸载完成！
echo ========================================
echo.
echo 请重新打开 CMD 窗口使环境变量生效。
echo.
pause
