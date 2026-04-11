@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  Smart Campus Service Platform - Windows Stop Script
::  stop.bat
:: ============================================================

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "PID_DIR=%PROJECT_DIR%\.pids"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=80"

echo.
echo ========================================
echo   Smart Campus - Stop Services
echo ========================================
echo.

set "STOPPED=0"

:: ----------------------------------------------------------
:: 1. Stop backend
:: ----------------------------------------------------------
echo [1/2] Stopping backend...

if exist "%PID_DIR%\backend.pid" (
    set /p BACKEND_PID=<"%PID_DIR%\backend.pid"
    tasklist /FI "PID eq !BACKEND_PID!" 2>nul | findstr "!BACKEND_PID!" >nul 2>&1
    if !errorlevel! equ 0 (
        taskkill /PID !BACKEND_PID! /T /F >nul 2>&1
        echo    [OK] Backend stopped (PID: !BACKEND_PID!)
        set /a STOPPED+=1
    ) else (
        echo    ~ Backend process no longer exists (PID: !BACKEND_PID!)
    )
    del "%PID_DIR%\backend.pid" >nul 2>&1
) else (
    set "FOUND_BACKEND=0"
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING" 2^>nul') do (
        taskkill /PID %%a /T /F >nul 2>&1
        echo    [OK] Backend stopped (PID: %%a)
        set /a STOPPED+=1
        set "FOUND_BACKEND=1"
    )
    if "!FOUND_BACKEND!"=="0" (
        echo    - Backend not running
    )
)

:: ----------------------------------------------------------
:: 2. Stop frontend
:: ----------------------------------------------------------
echo [2/2] Stopping frontend...

if exist "%PID_DIR%\frontend.pid" (
    set /p FRONTEND_PID=<"%PID_DIR%\frontend.pid"
    tasklist /FI "PID eq !FRONTEND_PID!" 2>nul | findstr "!FRONTEND_PID!" >nul 2>&1
    if !errorlevel! equ 0 (
        taskkill /PID !FRONTEND_PID! /T /F >nul 2>&1
        echo    [OK] Frontend stopped (PID: !FRONTEND_PID!)
        set /a STOPPED+=1
    ) else (
        echo    ~ Frontend process no longer exists (PID: !FRONTEND_PID!)
    )
    del "%PID_DIR%\frontend.pid" >nul 2>&1
) else (
    set "FOUND_FRONTEND=0"
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING" 2^>nul') do (
        taskkill /PID %%a /T /F >nul 2>&1
        echo    [OK] Frontend stopped (PID: %%a)
        set /a STOPPED+=1
        set "FOUND_FRONTEND=1"
    )
    if "!FOUND_FRONTEND!"=="0" (
        echo    - Frontend not running
    )
)

:: ----------------------------------------------------------
:: Status
:: ----------------------------------------------------------
echo.
echo ========================================
if !STOPPED! gtr 0 (
    echo   Stopped !STOPPED! service(s)
) else (
    echo   No running services found
)
echo ========================================
echo.
pause
