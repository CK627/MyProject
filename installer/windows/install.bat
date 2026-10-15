@echo off
rem ctfsweep installer (Windows) - one click: right-click this file, Run as ... (no admin needed)
rem
rem ASCII only on purpose: an UTF-8 .bat without BOM is parsed with the console ANSI
rem code page (GBK on a Chinese Windows), which splits multibyte characters across
rem line boundaries and makes cmd try to run fragments of the text.
rem All user-facing text comes from Python (which handles its own console encoding).
setlocal
set "ROOT=%~dp0..\.."
if not exist "%ROOT%\ctfsweep\__main__.py" (
    echo ERROR: ctfsweep package not found under "%ROOT%"
    echo        Run this file from a source snapshot or a repository checkout.
    exit /b 1
)
set "PYTHONPATH=%ROOT%"
python -B -m ctfsweep install %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo ERROR: install failed with code %RC%
exit /b %RC%
