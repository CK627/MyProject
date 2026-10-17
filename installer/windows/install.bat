@rem encoding: utf-8
@echo off
chcp 65001 >nul
rem startupctl 安装程序（Windows）— 右键本文件运行即可（不需要管理员）
rem
rem ASCII only on purpose: an UTF-8 .bat without BOM is parsed with the console ANSI
rem code page (GBK on a Chinese Windows), which splits multibyte characters across
rem line boundaries and makes cmd try to run fragments of the text.
rem All user-facing text comes from Python (which handles its own console encoding).
setlocal
set "ROOT=%~dp0..\.."
if not exist "%ROOT%\startupctl\__main__.py" (
    echo 错误: 在 "%ROOT%" 下找不到 startupctl 包
    echo        请在源码快照或仓库检出目录里运行本文件。
    exit /b 1
)
set "PYTHONPATH=%ROOT%"
python -B -m startupctl install %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo 错误: 安装失败，退出码 %RC%
exit /b %RC%
