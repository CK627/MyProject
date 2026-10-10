@echo off
rem ctfsweep 启动器（Windows）：把仓库根加入 PYTHONPATH 后交给 python 执行
setlocal
set "ROOT=%~dp0.."
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
python -B -m ctfsweep %*
