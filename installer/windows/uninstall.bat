@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM jtool uninstaller (Windows)

echo ========================================
echo   jtool uninstaller (Windows)
echo ========================================
echo.

REM ============================================
REM Confirm uninstall
REM ============================================
set /p "confirm=Uninstall jtool? (y/n): "
if /i not "!confirm!"=="y" (
    echo Cancelled
    pause
    exit /b 0
)

echo.

REM ============================================
REM Remove install dir
REM ============================================
set "INSTALL_DIR=C:\Program Files\devtools\jtool"

if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%"
    echo [Done] Removed %INSTALL_DIR%
) else (
    echo [Skip] Install dir not found
)

echo.

REM ============================================
REM Remove config file
REM ============================================
set "CONFIG_FILE=%USERPROFILE%\.jtool.conf"

if exist "%CONFIG_FILE%" (
    set /p "keep_config=Keep config file? (y/n): "
    if /i "!keep_config!"=="y" (
        echo [Skip] Kept config file %CONFIG_FILE%
    ) else (
        del "%CONFIG_FILE%"
        echo [Done] Removed %CONFIG_FILE%
    )
) else (
    echo [Skip] Config file not found
)

echo.

REM ============================================
REM Clean up environment
REM ============================================
echo [Env] Cleaning PATH...

REM Strip from the user PATH
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do (
    set "user_path=%%b"
    if defined user_path (
        set "user_path=!user_path:;%INSTALL_DIR%\bin=!"
        set "user_path=!user_path:%INSTALL_DIR%\bin;=!"
        set "user_path=!user_path:%INSTALL_DIR%\bin=!"
        reg add "HKCU\Environment" /v Path /t REG_EXPAND_SZ /d "!user_path!" /f >nul 2>&1
        echo [Done] Removed from user PATH
    )
)

echo.

REM ============================================
REM Uninstall complete
REM ============================================
echo ========================================
echo   Uninstall complete!
echo ========================================
echo.
echo Please reopen a CMD window for the PATH change to take effect.
echo.
pause
