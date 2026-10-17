@rem encoding: utf-8
@echo off
chcp 65001 >nul
rem startupctl 卸载程序（Windows）— 删除安装副本与 PATH 项。
rem 扫描缓存会保留；要清空请执行 "startupctl clear"。
rem ASCII only - see install.bat for why.
setlocal
set "PYTHONPATH=%USERPROFILE%\.devtools\startupctl\lib;%PYTHONPATH%"
python -B -m startupctl uninstall %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo 错误: 卸载失败，退出码 %RC%
exit /b %RC%
