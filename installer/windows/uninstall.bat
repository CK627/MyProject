@echo off
rem ctfsweep uninstaller (Windows) - removes the installed copy and the PATH entry.
rem Data (scan cache) is kept: use "ctfsweep clear" to wipe it.
rem ASCII only - see install.bat for why.
setlocal
set "PYTHONPATH=%USERPROFILE%\.devtools\ctfsweep\lib;%PYTHONPATH%"
python -B -m ctfsweep uninstall %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo ERROR: uninstall failed with code %RC%
exit /b %RC%
