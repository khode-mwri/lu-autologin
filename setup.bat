@echo off
title Lorestan University Auto-Login Setup
cls
echo ============================================================
echo   Lorestan University Auto-Login - Initial Setup
echo ============================================================
echo.
python "%~dp0lu_autologin.py"

echo.
echo ============================================================
echo Setup completed!
echo ============================================================
echo.
set /p STARTUP_CHOICE="Do you want this tool to start automatically with Windows? (Y/N): "
if /i "%STARTUP_CHOICE%"=="Y" (
    call "%~dp0enable_startup.bat"
) else (
    echo Auto-start skipped. You can enable it anytime by running enable_startup.bat.
)
echo.
echo You can now use:
echo  - run.bat            : Run in a visible window
echo  - run_background.bat : Run silently in the background
echo.
pause
