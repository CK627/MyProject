@echo off
chcp 65001 > nul
:: ============================================================
::  智慧校园服务平台 - Windows 卸载/清理脚本
:: ============================================================

set PROJECT_DIR=%~dp0..\..

echo ========================================
echo   智慧校园服务平台 - 卸载与环境清理 (Windows)
echo ========================================
echo   项目目录: %PROJECT_DIR%
echo.

echo 警告: 此操作将删除前端 node_modules, .next 构建缓存, 后端 venv 虚拟环境, Python 缓存以及所有日志文件。
echo 注意: 数据库文件 (campus.db) 和用户上传的附件将保留。
set /p confirm="确认要执行清理吗？(y/n): "

if /i "%confirm%" neq "y" (
    echo 已取消清理操作。
    pause
    exit /b 0
)

echo.
echo [1/4] 正在停止正在运行的服务...
call "%PROJECT_DIR%\scripts\Windows\stop.bat"

echo [2/4] 清理前端环境和构建文件...
if exist "%PROJECT_DIR%\node_modules" (
    rd /s /q "%PROJECT_DIR%\node_modules"
    echo    ✓ 已删除 node_modules
)
if exist "%PROJECT_DIR%\.next" (
    rd /s /q "%PROJECT_DIR%\.next"
    echo    ✓ 已删除 .next 构建缓存
)

echo [3/4] 清理后端环境和缓存...
if exist "%PROJECT_DIR%\backend\venv" (
    rd /s /q "%PROJECT_DIR%\backend\venv"
    echo    ✓ 已删除后端 venv 虚拟环境
)
:: 删除所有 __pycache__ 目录
for /d /r "%PROJECT_DIR%" %%d in (__pycache__) do (
    if exist "%%d" (
        rd /s /q "%%d"
    )
)
echo    ✓ 已清理 Python 缓存 (__pycache__)

echo [4/4] 清理日志文件...
del /q "%PROJECT_DIR%\*.log" 2>nul
echo    ✓ 已删除日志文件

echo.
echo ========================================
echo   环境清理完成！
echo   现在你可以将整个项目目录打包分享给他人了。
echo ========================================
pause
