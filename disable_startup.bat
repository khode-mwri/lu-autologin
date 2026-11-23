@echo off
title Disable Auto-Login from Windows Startup
set "STARTUP_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\lu_autologin.vbs"
if exist "%STARTUP_VBS%" (
    del /f /q "%STARTUP_VBS%" >nul 2>&1
    echo.
    echo [OK] Auto-login removed from Windows Startup.
    echo.
) else (
    echo Auto-login was not present in Windows Startup.
)
ping 127.0.0.1 -n 4 >nul
