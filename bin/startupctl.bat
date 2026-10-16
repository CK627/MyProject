@echo off
rem startupctl launcher (Windows): put the checkout root on PYTHONPATH, then run the package.
rem ASCII only, and CRLF line endings -- both are load-bearing. cmd decodes a *called*
rem batch file using the caller's code page, so a UTF-8 comment on a GBK console gets
rem split across line boundaries and cmd tries to execute fragments of the text. That
rem is why no Chinese appears here: all user-facing text is printed by Python, which
rem handles its own console encoding.
setlocal
set "ROOT=%~dp0.."
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
python -B -m startupctl %*
