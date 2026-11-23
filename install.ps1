# Lorestan University Auto-Login - One-Line PowerShell Installer
# Usage: irm https://raw.githubusercontent.com/khode-mwri/lu-autologin/main/install.ps1 | iex

$ErrorActionPreference = 'Stop'

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Lorestan University (LU) Auto-Login Installer" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verify Python availability
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$pythonwCmd = Get-Command pythonw -ErrorAction SilentlyContinue

if (-not $pythonCmd -or -not $pythonwCmd) {
    Write-Host "[ERROR] Python was not found on this system." -ForegroundColor Red
    Write-Host "Please install Python 3 from https://www.python.org/downloads/ or Microsoft Store." -ForegroundColor Yellow
    Write-Host "Remember to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    return
}

# 2. Installation directory
$installDir = Join-Path $HOME "LU_AutoLogin"
if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
}

# 3. Prompt for credentials securely
Write-Host "Enter your university credentials (stored locally in config.json):" -ForegroundColor White
$username = Read-Host "Student ID (Username)"
if ([string]::IsNullOrWhiteSpace($username)) {
    Write-Host "[ERROR] Student ID cannot be empty." -ForegroundColor Red
    return
}

$passwordSecure = Read-Host "Password" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($passwordSecure)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
if ([string]::IsNullOrWhiteSpace($plainPassword)) {
    Write-Host "[ERROR] Password cannot be empty." -ForegroundColor Red
    return
}

# 4. Fetch latest project files from GitHub
Write-Host "`nDownloading latest files from repository..." -ForegroundColor Cyan
$baseUrl = "https://raw.githubusercontent.com/khode-mwri/lu-autologin/main"
$files = @("lu_autologin.py", "autologin.bat", "run.bat", "run_background.bat", "stop_background.bat", "enable_startup.bat", "disable_startup.bat", "view_logs.bat", "setup.bat", "launch_silent.vbs", "README.md")

foreach ($f in $files) {
    $url = "$baseUrl/$f"
    $dest = Join-Path $installDir $f
    try {
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
    } catch {
        Write-Host "[WARNING] Could not fetch $f" -ForegroundColor Yellow
    }
}

# 5. Create local configuration file
$cfg = @{
    username = $username.Trim()
    password = $plainPassword.Trim()
    check_interval_seconds = 20
    proactive_renew_minutes = 110
}
$cfgJson = $cfg | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $installDir "config.json"), $cfgJson, [System.Text.Encoding]::UTF8)

# 6. Configure Windows Startup
$startupFolder = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup")
$startupVbs = Join-Path $startupFolder "lu_autologin.vbs"
$vbsContent = "Set WshShell = CreateObject(`"WScript.Shell`")`nWshShell.Run `"pythonw.exe `"`"$installDir\lu_autologin.py`"`", 0, False"
[System.IO.File]::WriteAllText($startupVbs, $vbsContent, [System.Text.Encoding]::ASCII)

# 8. Add installation directory to user PATH so `autologin` works from any cmd window
$currentPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($currentPath -and -not $currentPath.Contains($installDir)) {
    [Environment]::SetEnvironmentVariable('Path', "$currentPath;$installDir", 'User')
    Write-Host "[OK] Added $installDir to your user PATH." -ForegroundColor Green
}

# 9. Stop any older instance & start background service
# NOTE: wmic is removed from newer Windows 11 builds, so use CIM instead.
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -like '*lu_autologin.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 400

Start-Process "pythonw.exe" -ArgumentList "`"$installDir\lu_autologin.py`"" -WindowStyle Hidden

Write-Host ""
Write-Host "[OK] Installation completed successfully!" -ForegroundColor Green
Write-Host "[OK] Service is now running silently in the background." -ForegroundColor Green
Write-Host "[OK] Added to Windows Startup (auto-runs on system boot)." -ForegroundColor Green
Write-Host "Directory: $installDir" -ForegroundColor Gray
Write-Host "Reopen cmd and type: autologin   (opens the settings panel)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
