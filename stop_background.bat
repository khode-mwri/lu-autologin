@echo off
title Stop Auto-Login Service
echo Stopping background auto-login service...
REM NOTE: wmic is removed from newer Windows 11 builds, so use CIM via PowerShell.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -like '*lu_autologin.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
echo [OK] Background service stopped.
ping 127.0.0.1 -n 3 >nul
