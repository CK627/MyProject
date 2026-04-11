@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  Smart Campus Service Platform - Windows Start Script
::  start.bat
:: ============================================================

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "BACKEND_DIR=%PROJECT_DIR%\backend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=80"
set "BACKEND_LOG=%PROJECT_DIR%\backend.log"
set "FRONTEND_LOG=%PROJECT_DIR%\frontend.log"
set "PID_DIR=%PROJECT_DIR%\.pids"

echo.
echo ========================================
echo   Smart Campus - Start
echo ========================================
echo   Project: %PROJECT_DIR%
echo.

if not exist "%PID_DIR%" mkdir "%PID_DIR%"

:: ----------------------------------------------------------
:: 1. Stop existing processes
:: ----------------------------------------------------------
echo [1/4] Stopping existing services...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    echo    Stopped old backend process (PID: %%a)
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    echo    Stopped old frontend process (PID: %%a)
)

timeout /t 2 /nobreak >nul

:: ----------------------------------------------------------
:: 2. Check venv
:: ----------------------------------------------------------
if not exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    echo    [X] Python venv not found
    echo    Please run install.bat first
    pause
    exit /b 1
)

:: ----------------------------------------------------------
:: 3. Start backend - write log to file, show on failure
:: ----------------------------------------------------------
echo [2/4] Starting backend (port: %BACKEND_PORT%)...

cd /d "%BACKEND_DIR%"

:: Clear old log
if exist "%BACKEND_LOG%" del "%BACKEND_LOG%"

:: Write launcher bat to avoid quote issues
(
    echo @echo off
    echo cd /d "%BACKEND_DIR%"
    echo venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% ^> "%BACKEND_LOG%" 2^>^&1
) > "%BACKEND_DIR%\_run_backend.bat"

start "Backend" /min "%BACKEND_DIR%\_run_backend.bat"

:: Poll up to 15 seconds
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
    echo.
    echo    ============ FULL BACKEND LOG ============
    if exist "%BACKEND_LOG%" (
        type "%BACKEND_LOG%"
    ) else (
        echo    Log file not found - process may have crashed immediately
        echo    Try running manually:
        echo      cd "%BACKEND_DIR%"
        echo      venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT%
    )
    echo    ==========================================
    echo.
    pause
    exit /b 1
)

:: ----------------------------------------------------------
:: 4. Start frontend
:: ----------------------------------------------------------
echo [3/4] Starting frontend (port: %FRONTEND_PORT%)...

cd /d "%PROJECT_DIR%"

if not exist ".next" (
    echo    Frontend not built, running npm run build...
    call npm run build
    if %errorlevel% neq 0 (
        echo    [X] Frontend build failed
        pause
        exit /b 1
    )
)

if exist "%FRONTEND_LOG%" del "%FRONTEND_LOG%"

(
    echo @echo off
    echo cd /d "%PROJECT_DIR%"
    echo npx next start -p %FRONTEND_PORT% ^> "%FRONTEND_LOG%" 2^>^&1
) > "%PROJECT_DIR%\_run_frontend.bat"

start "Frontend" /min "%PROJECT_DIR%\_run_frontend.bat"

:: Poll up to 20 seconds
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
    echo.
    echo    ============ FULL FRONTEND LOG ============
    if exist "%FRONTEND_LOG%" (
        type "%FRONTEND_LOG%"
    ) else (
        echo    Log file not found
    )
    echo    ===========================================
    echo.
    pause
    exit /b 1
)

:: ----------------------------------------------------------
:: 5. Done
:: ----------------------------------------------------------
echo [4/4] Service status check...
echo.
echo ========================================
echo   Services started successfully
echo ========================================
echo   Backend API:  http://localhost:%BACKEND_PORT%
echo   Frontend:     http://localhost:%FRONTEND_PORT%
echo   API Docs:     http://localhost:%BACKEND_PORT%/docs
echo ========================================
echo.
echo   Backend log:  %BACKEND_LOG%
echo   Frontend log: %FRONTEND_LOG%
echo   Stop:         stop.bat
echo.

echo Opening browser in 3 seconds...
timeout /t 3 /nobreak >nul
start http://localhost:%FRONTEND_PORT%

pause
