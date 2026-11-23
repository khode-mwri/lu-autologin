@echo off
REM Lorestan University Auto-Login - command-line panel.
REM After install, the install folder is on your user PATH, so just type:
REM   autologin
REM in any cmd window.
REM UTF-8 code page so Persian text displays correctly in the console.
chcp 65001 >nul
python "%~dp0lu_autologin.py" --panel
