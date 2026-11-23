# Lorestan University Auto-Login - Uninstaller
# Usage: irm https://raw.githubusercontent.com/khode-mwri/lu-autologin/main/uninstall.ps1 | iex

Write-Host "Stopping background service..." -ForegroundColor Yellow
# NOTE: wmic is removed from newer Windows 11 builds, so use CIM instead.
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -like '*lu_autologin.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

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

# Remove the installation directory from the user PATH (best effort).
$currentPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($currentPath -and $currentPath.Contains($installDir)) {
    $newPath = ($currentPath -split ';' | Where-Object { $_ -ne $installDir -and $_ -ne '' }) -join ';'
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    Write-Host "[OK] Removed installation directory from PATH." -ForegroundColor Green
}

Write-Host "[OK] Lorestan University Auto-Login has been completely removed." -ForegroundColor Green
