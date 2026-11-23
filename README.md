# Lorestan University Internet Auto-Login

A lightweight Python tool that automates login and session keep-alive for Lorestan University's internet gateway (`internet.lu.ac.ir`).

## ⚡ Quick One-Line Install (PowerShell)

Open PowerShell on any Windows PC and run:

```powershell
irm https://raw.githubusercontent.com/khode-mwri/lu-autologin/main/install.ps1 | iex
```

It will ask for your Student ID and Password once, set up everything, add the script to Windows Startup, and start running silently in the background!

To completely uninstall anytime:
```powershell
irm https://raw.githubusercontent.com/khode-mwri/lu-autologin/main/uninstall.ps1 | iex
```

---

## Highlights
- **Automatic Reconnection**: Detects when connectivity drops and logs back in.
- **Proactive Session Renewal**: Renews the session before the university's 2-hour timeout.
- **Background Execution**: Operates without keeping any terminal windows open.
- **Browser-Independent**: Directly interacts with the login endpoint without requiring a browser.
- **Windows Startup Integration**: Launches silently on boot.

## Manual Usage Scripts
Located in `$HOME\LU_AutoLogin` after install:
- `run.bat`: Runs the script with visible logs in a console window.
- `run_background.bat`: Runs the script silently in the background.
- `stop_background.bat`: Stops running background instances.
- `enable_startup.bat`: Registers the background script to start on Windows logon.
- `disable_startup.bat`: Removes the script from Windows startup.
- `view_logs.bat`: Opens `autologin.log` to review connection history.

## Configuration
Credentials and settings are saved locally in `config.json`:
```json
{
  "username": "YOUR_STUDENT_ID",
  "password": "YOUR_PASSWORD",
  "check_interval_seconds": 20,
  "proactive_renew_minutes": 110
}
```
*Note: `config.json` is strictly ignored by git to protect personal credentials.*
