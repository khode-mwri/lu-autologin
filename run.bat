@echo off
title Lorestan University Auto-Login
cls
echo ============================================================
echo   Lorestan University (LU) Internet Auto-Login Service
echo ============================================================
echo.
echo Keeping your university internet session active and reconnecting
echo automatically every 2 hours to prevent interrupted downloads.
echo.
echo Press Ctrl + C at any time to stop.
echo.
python "%~dp0lu_autologin.py"
pause
