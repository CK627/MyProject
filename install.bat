@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  Smart Campus Service Platform - Windows Install Script
::  install.bat
:: ============================================================

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "BACKEND_DIR=%PROJECT_DIR%\backend"

echo.
echo ========================================
echo   Smart Campus - Windows Install
echo ========================================
echo   Project: %PROJECT_DIR%
echo ========================================
echo.

:: ----------------------------------------------------------
:: 1. Check Python
:: ----------------------------------------------------------
echo [1/6] Checking Python...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo    [X] Python not found!
    echo.
    echo    Please install Python 3.10+:
    echo      https://www.python.org/downloads/
    echo      Make sure to check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYTHON_VER=%%v"
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VER%") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)

if %PY_MAJOR% lss 3 (
    echo    [X] Python version too low: %PYTHON_VER%, need 3.10+
    pause
    exit /b 1
)
if %PY_MAJOR% equ 3 if %PY_MINOR% lss 10 (
    echo    [X] Python version too low: %PYTHON_VER%, need 3.10+
    pause
    exit /b 1
)

echo    [OK] Python %PYTHON_VER%
echo.

:: ----------------------------------------------------------
:: 2. Check Node.js
:: ----------------------------------------------------------
echo [2/6] Checking Node.js...

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo    [X] Node.js not found!
    echo.
    echo    Please install Node.js 18+:
    echo      https://nodejs.org/
    echo.
    pause
    exit /b 1
)

for /f "tokens=1 delims=." %%v in ('node -v') do set "NODE_MAJOR=%%v"
set "NODE_MAJOR=%NODE_MAJOR:v=%"

if %NODE_MAJOR% lss 18 (
    echo    [X] Node.js version too low, need 18+
    pause
    exit /b 1
)

for /f %%v in ('node -v') do set "NODE_VER=%%v"
for /f %%v in ('npm -v') do set "NPM_VER=%%v"

echo    [OK] Node.js %NODE_VER%
echo    [OK] npm %NPM_VER%
echo.

:: ----------------------------------------------------------
:: 3. Setup backend Python venv + dependencies
:: ----------------------------------------------------------
echo [3/6] Setting up backend...

cd /d "%BACKEND_DIR%"

if not exist "venv" (
    echo    Creating Python virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo    [X] Failed to create venv
        pause
        exit /b 1
    )
)

echo    Upgrading pip...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q

echo    Installing bcrypt (binary wheel)...
pip install --only-binary :all: bcrypt>=4.2.0 -q 2>nul
if %errorlevel% neq 0 (
    echo    [!] Binary install failed, trying normal install...
    pip install bcrypt>=4.2.0 -q
)

echo    Installing backend dependencies...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo    [X] Backend dependency install failed
    echo.
    echo    Solutions:
    echo      1. Use Python 3.12 instead of 3.13
    echo      2. Install Visual C++ Build Tools:
    echo         https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo      3. Install Rust: https://rustup.rs/
    echo.
    call deactivate
    pause
    exit /b 1
)

:: Verify key dependencies
python -c "import fastapi; import uvicorn; import sqlalchemy; import pymysql; print('OK')" >nul 2>&1
if %errorlevel% neq 0 (
    echo    [X] Backend dependency verification failed
    call deactivate
    pause
    exit /b 1
)

call deactivate
echo    [OK] Backend dependencies installed
echo.

:: ----------------------------------------------------------
:: 4. Database config (interactive)
:: ----------------------------------------------------------
echo [4/6] Database configuration...

set "CONFIG_FILE=%BACKEND_DIR%\app\config.py"

:: Check if config already exists
set "NEED_CONFIG=0"
if not exist "%CONFIG_FILE%" set "NEED_CONFIG=1"

if exist "%CONFIG_FILE%" (
    echo    Config file found: %CONFIG_FILE%
    set /p "RECONFIG=   Reconfigure database? (y/N): "
    if /i "!RECONFIG!"=="y" set "NEED_CONFIG=1"
)

if "!NEED_CONFIG!"=="0" (
    echo    Skipped, using existing config
    goto :skip_db_config
)

echo.
echo    Enter MySQL database connection details:
echo    (Press Enter to use the default value in brackets)
echo.
set /p "DB_HOST=   DB Host [localhost]: "
if "!DB_HOST!"=="" set "DB_HOST=localhost"

set /p "DB_PORT=   DB Port [3306]: "
if "!DB_PORT!"=="" set "DB_PORT=3306"

set /p "DB_USER=   DB User [root]: "
if "!DB_USER!"=="" set "DB_USER=root"

set /p "DB_PASSWORD=   DB Password: "

set /p "DB_NAME=   DB Name [smart_campus]: "
if "!DB_NAME!"=="" set "DB_NAME=smart_campus"

set /p "JWT_KEY=   JWT Secret [auto-generate]: "
if "!JWT_KEY!"=="" (
    cd /d "%BACKEND_DIR%"
    call venv\Scripts\activate.bat
    for /f %%k in ('python -c "import secrets; print(secrets.token_urlsafe(32))"') do set "JWT_KEY=%%k"
    call deactivate
)

:: Write config using the bundled Python helper script
cd /d "%BACKEND_DIR%"
call venv\Scripts\activate.bat

python "%PROJECT_DIR%\_write_config.py" "!DB_HOST!" "!DB_PORT!" "!DB_USER!" "!DB_PASSWORD!" "!DB_NAME!" "!JWT_KEY!" "%CONFIG_FILE%"
if %errorlevel% neq 0 (
    echo    [X] Failed to write config file
    call deactivate
    pause
    exit /b 1
)
call deactivate

echo    [OK] Database config updated
:skip_db_config
echo.

:: ----------------------------------------------------------
:: 5. Install frontend dependencies
:: ----------------------------------------------------------
echo [5/6] Installing frontend dependencies...

cd /d "%PROJECT_DIR%"

if not exist "node_modules" (
    echo    Running npm install...
    call npm install
    if %errorlevel% neq 0 (
        echo    [X] Frontend dependency install failed
        pause
        exit /b 1
    )
) else (
    echo    node_modules exists, skipping install
    echo    Delete node_modules and rerun to reinstall
)

echo    [OK] Frontend dependencies installed
echo.

:: ----------------------------------------------------------
:: 6. Build frontend
:: ----------------------------------------------------------
echo [6/6] Building frontend...

cd /d "%PROJECT_DIR%"
call npm run build
if %errorlevel% neq 0 (
    echo    [X] Frontend build failed
    pause
    exit /b 1
)

echo    [OK] Frontend build complete
echo.

:: ----------------------------------------------------------
:: Done
:: ----------------------------------------------------------
echo ========================================
echo   Install complete!
echo ========================================
echo.
echo   Start:   start.bat
echo   Stop:    stop.bat
echo   Restart: reboot.bat
echo.
echo   Ports:
echo     Frontend: 80
echo     Backend:  8000
echo.
echo   Notes:
echo     1. Make sure MySQL database exists (smart_campus)
echo     2. Make sure ports 80 and 8000 are available
echo     3. Backend will auto-create tables on first run
echo ========================================
echo.
pause
