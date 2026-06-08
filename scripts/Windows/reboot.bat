@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  Smart Campus Service Platform - Windows Restart Script
::  reboot.bat (with frontend rebuild)
:: ============================================================

set "PROJECT_DIR=%~dp0..\.."
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "BACKEND_DIR=%PROJECT_DIR%\backend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=80"
set "PID_DIR=%PROJECT_DIR%\.pids"

echo.
echo ========================================
echo   Smart Campus - Restart
echo ========================================
echo   Project: %PROJECT_DIR%
echo.

if not exist "%PID_DIR%" mkdir "%PID_DIR%"

:: ----------------------------------------------------------
:: 1. Stop existing services
:: ----------------------------------------------------------
echo [1/5] Stopping existing services...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    echo    Stopped backend (PID: %%a)
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    echo    Stopped frontend (PID: %%a)
)

del "%PID_DIR%\backend.pid" >nul 2>&1
del "%PID_DIR%\frontend.pid" >nul 2>&1
timeout /t 2 /nobreak >nul

:: ----------------------------------------------------------
:: 2. Rebuild frontend
:: ----------------------------------------------------------
echo [2/5] Rebuilding frontend...

cd /d "%PROJECT_DIR%"
call npm run build
if %errorlevel% neq 0 (
    echo    [X] Frontend build failed
    pause
    exit /b 1
)
echo    [OK] Frontend build complete

:: ----------------------------------------------------------
:: 3. Start backend
:: ----------------------------------------------------------
echo [3/5] Starting backend (port: %BACKEND_PORT%)...

if not exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    echo    [X] Python venv not found, please run install.bat first
    pause
    exit /b 1
)

echo @echo off > "%BACKEND_DIR%\_run_backend.bat"
echo cd /d "%BACKEND_DIR%" >> "%BACKEND_DIR%\_run_backend.bat"
echo venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% >> "%BACKEND_DIR%\_run_backend.bat"

start "Backend" /min "%BACKEND_DIR%\_run_backend.bat"

echo    Waiting for backend to start...
set "BACKEND_RUNNING=0"
for /l %%i in (1,1,15) do (
    if "!BACKEND_RUNNING!"=="0" (
        timeout /t 1 /nobreak >nul
        for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING" 2^>nul') do (
            set "BACKEND_RUNNING=1"
            echo %%a> "%PID_DIR%\backend.pid"
            echo    [OK] Backend started (PID: %%a)
        )
    )
)

if "!BACKEND_RUNNING!"=="0" (
    echo    [X] Backend failed to start after 15 seconds
    echo    Please check the Backend window for error details.
    pause
    exit /b 1
)

:: ----------------------------------------------------------
:: 4. Start frontend
:: ----------------------------------------------------------
echo [4/5] Starting frontend (port: %FRONTEND_PORT%)...

cd /d "%PROJECT_DIR%"

echo @echo off > "%PROJECT_DIR%\_run_frontend.bat"
echo cd /d "%PROJECT_DIR%" >> "%PROJECT_DIR%\_run_frontend.bat"
echo npx next start -p %FRONTEND_PORT% >> "%PROJECT_DIR%\_run_frontend.bat"

start "Frontend" /min "%PROJECT_DIR%\_run_frontend.bat"

echo    Waiting for frontend to start...
set "FRONTEND_RUNNING=0"
for /l %%i in (1,1,20) do (
    if "!FRONTEND_RUNNING!"=="0" (
        timeout /t 1 /nobreak >nul
        for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING" 2^>nul') do (
            set "FRONTEND_RUNNING=1"
            echo %%a> "%PID_DIR%\frontend.pid"
            echo    [OK] Frontend started (PID: %%a)
        )
    )
)

if "!FRONTEND_RUNNING!"=="0" (
    echo    [X] Frontend failed to start after 20 seconds
    echo    Please check the Frontend window for error details.
    pause
    exit /b 1
)

:: ----------------------------------------------------------
:: 5. Done
:: ----------------------------------------------------------
echo [5/5] Service status check...
echo.
echo ========================================
echo   Services restarted successfully
echo ========================================
echo   Backend API:  http://localhost:%BACKEND_PORT%
echo   Frontend:     http://localhost:%FRONTEND_PORT%
echo   API Docs:     http://localhost:%BACKEND_PORT%/docs
echo ========================================
echo.
echo   To stop services: stop.bat
echo.

pause
