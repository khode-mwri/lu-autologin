# Lorestan University Auto-Login - Uninstaller
# Usage: irm https://raw.githubusercontent.com/khode-mwri/lu-autologin/main/uninstall.ps1 | iex

Write-Host "Stopping background service..." -ForegroundColor Yellow
wmic process where "name='pythonw.exe' and commandline like '%lu_autologin.py%'" call terminate >$null 2>&1

$startupFolder = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup")
$startupVbs = Join-Path $startupFolder "lu_autologin.vbs"
if (Test-Path $startupVbs) {
    Remove-Item -Path $startupVbs -Force
    Write-Host "[OK] Removed from Windows Startup." -ForegroundColor Green
}

$installDir = Join-Path $HOME "LU_AutoLogin"
if (Test-Path $installDir) {
    Remove-Item -Path $installDir -Recurse -Force
    Write-Host "[OK] Removed installation directory: $installDir" -ForegroundColor Green
}

Write-Host "[OK] Lorestan University Auto-Login has been completely removed." -ForegroundColor Green
