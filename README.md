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

## Settings panel — just type `autologin`

After install, reopen cmd and type:

```
autologin
```

A panel opens where you can:
- Start / stop the background service
- Enable / disable run on Windows startup
- Switch language (فارسی / English)
- Change username, password, check interval, renewal time
- Test login now, diagnose the portal, view logs

---

## Highlights
- **Automatic Reconnection**: Detects when connectivity drops and logs back in.
- **Proactive Session Renewal**: Renews the session before the university's 2-hour timeout.
- **Multi-Strategy Login**: The portal's exact shape can vary (CHAP on/off, chap-id as raw byte / octal / hex escape, form posting to the page or to a different URL, HTTP/HTTPS). The script detects what the page actually contains and tries every plausible method — CHAP form POST, plain form POST, plain page POST, CHAP page POST, GET login — until one is **verified** by a real internet check. The winning method is remembered in `config.json` and tried first next time.
- **Background Execution**: Operates without keeping any terminal windows open.
- **Browser-Independent**: Directly interacts with the login endpoint without requiring a browser.
- **Windows Startup Integration**: Launches silently on boot.

## If login does not work

Run the diagnose mode once while on university Wi-Fi — it fetches the portal, prints the forms and CHAP data it found, and saves the page to `portal_debug.html`:

```powershell
python lu_autologin.py --diagnose
```

Other useful modes:

```powershell
python lu_autologin.py --once                        # try once, then exit
python lu_autologin.py --once --strategy chap-form   # force one method
```

If every method fails, the log (`autologin.log`) and `portal_debug.html` show exactly what the portal returned — that is what is needed to add the missing method. A test suite (`tests/`) verifies all login methods against a mock MikroTik portal; run it with `python tests/run_strategy_tests.py`.

## Manual Usage Scripts
Located in `$HOME\LU_AutoLogin` after install:
- `autologin.bat`: Opens the interactive settings panel (`autologin` command).
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
  "proactive_renew_minutes": 110,
  "portal_urls": ["https://internet.lu.ac.ir/login", "http://internet.lu.ac.ir/login"],
  "connectivity_urls": ["http://clients3.google.com/generate_204", "http://detectportal.firefox.com/success.txt", "http://www.msftconnecttest.com/connecttest.txt"]
}
```
*Note: `config.json` is strictly ignored by git to protect personal credentials. The script also remembers the login method that worked (`"strategy"`) in `config.json` and tries it first next time.*
