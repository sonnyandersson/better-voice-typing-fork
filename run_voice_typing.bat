@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Voice Typing
cd "%~dp0"

set "APP=voice_typing.pyw"
set "LOCK=%TEMP%\voice_typing_app.lock"
set "PYW=%CD%\.venv\Scripts\pythonw.exe"

echo Starting Better Voice Typing...

REM Always terminate any existing instances from this venv (safe: filters by exact executable path)
powershell -NoProfile -Command "$p = '%PYW%'; $procs = Get-Process -Name pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $p }; if ($procs) { $procs | Stop-Process -Force -PassThru | Out-Null; for ($i=0; $i -lt 10; $i++) { if (-not (Get-Process -Name pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $p })) { break }; Start-Sleep -Seconds 1 } }" >nul 2>&1
if exist "%LOCK%" del /f /q "%LOCK%" >nul 2>&1

start "" "%PYW%" "%CD%\%APP%"
echo    Application (re)started. Look for the tray icon.
echo    If it doesn't appear within ~10 seconds, run this script again.

echo.
echo Press any key to close this window...
pause >nul
endlocal
