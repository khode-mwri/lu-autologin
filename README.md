# Lorestan University Internet Auto-Login

A lightweight Python tool that automates login and session keep-alive for Lorestan University's internet gateway (`internet.lu.ac.ir`).

## Highlights
- **Automatic Reconnection**: Detects when connectivity drops and logs back in.
- **Proactive Session Renewal**: Renews the session before the university's 2-hour timeout.
- **Background Execution**: Operates without keeping any terminal windows open.
- **Browser-Independent**: Directly interacts with the login endpoint without requiring a browser.
- **Windows Startup Integration**: Option to launch silently on boot.

## Quick Start

1. Clone or download this repository.
2. Run `setup.bat` (first-time only) and enter your Student ID and Password when prompted.
3. Choose whether to start automatically with Windows.

### Available Scripts
- `setup.bat`: Interactive setup to configure your credentials in `config.json`.
- `run.bat`: Runs the script with visible logs in a console window.
- `run_background.bat`: Runs the script silently in the background.
- `stop_background.bat`: Stops any running background instances.
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
*Note: `config.json` is ignored by git to protect personal credentials.*
