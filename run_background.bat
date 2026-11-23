@echo off
title Launch Auto-Login in Background
start "" pythonw "%~dp0lu_autologin.py"
echo.
echo [OK] Auto-Login service started successfully in the background!
echo It will keep running silently with no open console windows.
echo.
echo - To view activity logs, run: view_logs.bat
echo - To stop the service, run  : stop_background.bat
echo.
ping 127.0.0.1 -n 4 >nul
