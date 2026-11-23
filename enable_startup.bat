@echo off
title Enable Auto-Login on Windows Startup
set "STARTUP_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\lu_autologin.vbs"

(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run "pythonw.exe ""%~dp0lu_autologin.py""", 0, False
) > "%STARTUP_VBS%"

if exist "%STARTUP_VBS%" (
    echo.
    echo [OK] Auto-login added to Windows Startup successfully!
    echo It will start automatically and silently every time Windows turns on.
    echo.
) else (
    echo [ERROR] Could not write to startup folder.
)
ping 127.0.0.1 -n 4 >nul
