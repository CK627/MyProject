@rem encoding: utf-8
@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM Build the Inno Setup installer on Windows.
REM Transferred and invoked by build-from-mac.sh.
REM
REM Deliberately ASCII-only, and deliberately a .bat rather than a .ps1:
REM   * A UTF-8 .bat without a BOM gets parsed with the console ANSI code page
REM     (GBK on a Chinese Windows), which splits multibyte characters across
REM     line boundaries and makes cmd try to run fragments of the text.
REM   * A PowerShell script would need -ExecutionPolicy Bypass to run, which
REM     disables the script-execution security control on the target machine.

set "TOOL=%~1"
if "%TOOL%"=="" set "TOOL=startupctl"

set "WORKDIR=%~dp0"
set "WORKDIR=%WORKDIR:~0,-1%"

echo ==> 工作目录: %WORKDIR%

call :find_iscc

if not defined ISCC (
    echo ==> 未找到 Inno Setup，正在安装

    REM The installer is fetched by build-from-mac.sh and shipped alongside the
    REM sources: this machine cannot reach GitHub's release CDN directly
    REM (curl: (35) Recv failure: Connection was reset).
    REM Do NOT use jrsoftware.org/download.php/is.exe either -- that returns an
    REM HTML interstitial (~10 KB), not the installer.
    if exist "%WORKDIR%\innosetup.exe" (
        echo     正在运行随包安装程序...
        "%WORKDIR%\innosetup.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
        call :find_iscc
    )

    if not defined ISCC (
        echo     随包安装失败，改试 winget...
        where winget >nul 2>&1
        if !errorlevel! equ 0 (
            winget install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements
            call :find_iscc
        )
    )

    if not defined ISCC (
        echo 错误: 安装 Inno Setup 后仍找不到 ISCC.exe
        exit /b 1
    )
)

echo ==> ISCC: %ISCC%

cd /d "%WORKDIR%"
"%ISCC%" "%WORKDIR%\%TOOL%.iss"
if !errorlevel! neq 0 (
    echo 错误: ISCC 编译失败，退出码 !errorlevel!
    exit /b 1
)

set "EXE="
for %%f in ("%WORKDIR%\%TOOL%-setup-*.exe") do set "EXE=%%~ff"
if not defined EXE (
    echo 错误: 编译完成但找不到 %TOOL%-setup-*.exe
    exit /b 1
)

echo ==> 产物: !EXE!
exit /b 0

REM ---------------------------------------------------------------
REM Locate ISCC.exe.
REM Its path depends on whether Inno was installed for all users or
REM just the current one, so probe all known locations.
REM NOTE: the parentheses in %ProgramFiles(x86)% would close an if(...)
REM block early, so this must stay a non-parenthesised subroutine.
REM ---------------------------------------------------------------
:find_iscc
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
exit /b 0
