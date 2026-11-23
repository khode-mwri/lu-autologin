@echo off
title Stop Auto-Login Service
echo Stopping background auto-login service...
wmic process where "name='pythonw.exe' and commandline like '%%lu_autologin.py%%'" call terminate >nul 2>&1
echo [OK] Background service stopped.
ping 127.0.0.1 -n 3 >nul
