@echo off
if exist "%~dp0autologin.log" (
    start notepad "%~dp0autologin.log"
) else (
    echo No log file generated yet. Start the script first.
    pause
)
