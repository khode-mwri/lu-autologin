# ورود خودکار به اینترنت دانشگاه لرستان | Lorestan University Internet Auto-Login

ابزاری سبک به زبان پایتون که ورود به درگاه اینترنت دانشگاه لرستان (`internet.lu.ac.ir`) و زنده نگه‌داشتن نشست را خودکار می‌کند.
A lightweight Python tool that automates login and session keep-alive for Lorestan University's internet gateway (`internet.lu.ac.ir`).

> روی زبان موردنظرت کلیک کن | Click your language:

<details open>
<summary>🇮🇷 فارسی</summary>

## ⚡ نصب سریع

در PowerShell ویندوز این دستور را بزنید:

```powershell
irm https://raw.githubusercontent.com/khode-mwri/lu-autologin/main/install.ps1 | iex
```

یک بار شماره دانشجویی و پسورد را می‌پرسد، همه‌چیز را راه‌اندازی می‌کند، اسکریپت را به استارتاپ ویندوز اضافه می‌کند و در پس‌زمینه شروع به کار می‌کند.

حذف کامل در هر زمان:

```powershell
irm https://raw.githubusercontent.com/khode-mwri/lu-autologin/main/uninstall.ps1 | iex
```

## پنل تنظیمات — فقط بنویسید `autologin`

بعد از نصب، cmd را دوباره باز کنید و بنویسید:

```
autologin
```

پنلی باز می‌شود که می‌توانید در آن:

- سرویس را در پس‌زمینه شروع / متوقف کنید
- اجرای خودکار با ویندوز را فعال / غیرفعال کنید
- زبان را عوض کنید (فارسی / English)
- پنل همیشه به فارسی باز می‌شود
- نام کاربری، پسورد، فاصله‌ی بررسی و زمان تمدید را تغییر دهید
- همین حالا لاگین را تست کنید، پورتال را عیب‌یابی کنید و لاگ را ببینید
- به‌روزرسانی را بررسی کنید

**نکته درباره‌ی نمایش فارسی در ترمینال:** متن فارسی در Windows Terminal راست‌چین و به‌هم‌پیوسته نمایش داده می‌شود. در cmd قدیمی ممکن است حروف جدا یا جابه‌جا دیده شوند؛ در این صورت از Windows Terminal استفاده کنید یا از داخل پنل زبان را به English تغییر دهید.

## ویژگی‌ها

- **ورود مجدد خودکار:** وقتی اتصال قطع می‌شود متوجه می‌شود و دوباره لاگین می‌کند.
- **تمدید پیشگیرانه‌ی نشست:** نشست را پیش از مهلت ۲ ساعته‌ی دانشگاه تمدید می‌کند.
- **لاگین چندروشی:** شکل دقیق پورتال ممکن است فرق کند (CHAP روشن/خاموش، chap-id به‌صورت بایت خام / اکتال / هگز، فرم به صفحه‌ی خودش یا به آدرس دیگری پست شود، HTTP/HTTPS). اسکریپت بررسی می‌کند صفحه دقیقاً چه چیزی دارد و همه‌ی روش‌های ممکن را امتحان می‌کند — CHAP form POST، plain form POST، plain page POST، CHAP page POST، GET login — تا وقتی یکی با یک بررسی واقعی اینترنت **تأیید** شود. روش برنده در `config.json` ذخیره می‌شود و دفعه‌ی بعد اول امتحان می‌شود.
- **اجرای پس‌زمینه:** بدون اینکه پنجره‌ی ترمینالی باز بماند کار می‌کند.
- **مستقل از مرورگر:** مستقیم با نقطه‌ی ورود لاگین کار می‌کند و به مرورگر نیازی ندارد.
- **یکپارچه با استارتاپ ویندوز:** با روشن شدن سیستم، بی‌صدا اجرا می‌شود.
- **آیکون سینی ویندوز:** آیکون کوچکی کنار ساعت وضعیت را نشان می‌دهد (سبز = متصل، قرمز = قطع) و با کلیک راست می‌توانید لاگین، پنل یا خروج را بزنید.
- **اعلان:** اگر چند بار پشت سر هم لاگین نشد، ویندوز به شما خبر می‌دهد؛ وقتی دوباره وصل شد هم خبر می‌دهد.
- **به‌روزرسانی خودکار:** اسکریپت هر چند ساعت گیت‌هاب را چک می‌کند و اگر نسخه‌ی جدید آمد، خودش را به‌روز می‌کند.

## اگر لاگین کار نکرد

یک بار روی وای‌فای دانشگاه حالت عیب‌یابی را اجرا کنید — پورتال را می‌گیرد، فرم‌ها و داده‌های CHAP پیدا شده را چاپ می‌کند و صفحه را در `portal_debug.html` ذخیره می‌کند:

```powershell
python lu_autologin.py --diagnose
```

حالت‌های مفید دیگر:

```powershell
python lu_autologin.py --once                        # یک بار امتحان کن، بعد خارج شو
python lu_autologin.py --once --strategy chap-form   # فقط یک روش را امتحان کن
```

اگر همه‌ی روش‌ها شکست خوردند، لاگ (`autologin.log`) و `portal_debug.html` دقیقاً نشان می‌دهند پورتال چه چیزی برگردانده — همان چیزی که برای اضافه کردن روشِ جاافتاده لازم است. یک مجموعه تست (`tests/`) همه‌ی روش‌های لاگین را روی یک پورتال میکروتیک ساختگی بررسی می‌کند؛ با `python tests/run_strategy_tests.py` اجرا می‌شود.

## اسکریپت‌های دستی

بعد از نصب در `$HOME\LU_AutoLogin` قرار دارند:

- `autologin.bat`: باز کردن پنل تنظیمات تعاملی (دستور `autologin`).
- `run.bat`: اجرای اسکریپت با لاگ‌های قابل‌مشاهده در پنجره‌ی کنسول.
- `run_background.bat`: اجرای بی‌صدای اسکریپت در پس‌زمینه.
- `stop_background.bat`: توقف نمونه‌های در حال اجرای پس‌زمینه.
- `enable_startup.bat`: ثبت اسکریپت پس‌زمینه برای اجرا هنگام ورود به ویندوز.
- `disable_startup.bat`: حذف اسکریپت از استارتاپ ویندوز.
- `view_logs.bat`: باز کردن `autologin.log` برای بررسی تاریخچه‌ی اتصال.

## پیکربندی

نام کاربری و تنظیمات به‌صورت محلی در `config.json` ذخیره می‌شوند:

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

*توجه: `config.json` برای محافظت از اطلاعات شخصی کاملاً از گیت نادیده گرفته می‌شود. اسکریپت روش لاگینی که جواب داده (`"strategy"`) و زبان پنل (`"language"`) را هم در `config.json` ذخیره می‌کند و دفعه‌ی بعد اول همان روش را امتحان می‌کند.*

</details>

<details>
<summary>🇬🇧 English</summary>

## ⚡ Quick Install

Open PowerShell on any Windows PC and run:

```powershell
irm https://raw.githubusercontent.com/khode-mwri/lu-autologin/main/install.ps1 | iex
```

It will ask for your Student ID and Password once, set up everything, add the script to Windows Startup, and start running silently in the background!

To completely uninstall anytime:

```powershell
irm https://raw.githubusercontent.com/khode-mwri/lu-autologin/main/uninstall.ps1 | iex
```

## Settings panel — just type `autologin`

After install, reopen cmd and type:

```
autologin
```

A panel opens where you can:

- Start / stop the background service
- Enable / disable run on Windows startup
- Switch language (فارسی / English)
- The panel always opens in Persian
- Change username, password, check interval, renewal time
- Test login now, diagnose the portal, view logs
- Check for updates

**Note on Persian text in the terminal:** Persian renders right-aligned and properly shaped in Windows Terminal. In the old cmd console it may look broken; use Windows Terminal or switch the panel to English.

## Highlights

- **Automatic reconnection:** Detects when connectivity drops and logs back in.
- **Proactive session renewal:** Renews the session before the university's 2-hour timeout.
- **Multi-strategy login:** The portal's exact shape can vary (CHAP on/off, chap-id as raw byte / octal / hex escape, form posting to the page or to a different URL, HTTP/HTTPS). The script detects what the page actually contains and tries every plausible method — CHAP form POST, plain form POST, plain page POST, CHAP page POST, GET login — until one is **verified** by a real internet check. The winning method is remembered in `config.json` and tried first next time.
- **Background execution:** Operates without keeping any terminal windows open.
- **Browser-independent:** Directly interacts with the login endpoint without requiring a browser.
- **Windows Startup integration:** Launches silently on boot.
- **System tray icon:** A small icon next to the clock shows the status (green = connected, red = offline); right-click it to log in now, open the panel, or quit.
- **Notifications:** If login fails several times in a row, Windows lets you know; it also tells you when the connection is back.
- **Self-update:** The script checks GitHub every few hours and updates itself when a new version is out.

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

## Manual usage scripts

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

*Note: `config.json` is strictly ignored by git to protect personal credentials. The script also remembers the login method that worked (`"strategy"`) and the panel language (`"language"`) in `config.json`, and tries the winning method first next time.*

</details>

---

## آموزش استفاده | How to use

**فارسی:**

1. **نصب:** دستور یک‌خطی بالا را در PowerShell بزن و شماره دانشجویی و پسوردت را وارد کن.
2. **تمام:** از اینجا به بعد اسکریپت خودش در پس‌زمینه کار می‌کند و آیکونش کنار ساعت دیده می‌شود (سبز یعنی متصل، قرمز یعنی قطع)؛ هر وقت اینترنت قطع شود خودش دوباره لاگین می‌کند، و با روشن شدن ویندوز هم خودش اجرا می‌شود.
3. **تنظیمات:** هر وقت خواستی چیزی را عوض کنی، cmd را باز کن و بنویس `autologin` — پنل باز می‌شود (استارتاپ، زبان، پسورد، فاصله‌ی بررسی و...).
4. **اولین تست:** روی وای‌فای دانشگاه، از داخل پنل «عیب‌یابی» را بزن (یا `python lu_autologin.py --diagnose`) تا مطمئن شوی لاگین جواب می‌دهد.
5. **اگر کار نکرد:** فایل‌های `autologin.log` و `portal_debug.html` را نگه دار؛ با آن‌ها می‌شود روشِ جاافتاده را اضافه کرد.

**نکته:** اسکریپت هر چند ساعت گیت‌هاب را چک می‌کند و اگر نسخه‌ی جدید آمد، خودش را به‌روز می‌کند؛ برای بررسی دستی هم از پنل گزینه‌ی «بررسی به‌روزرسانی» را بزن.

**English:**

1. **Install:** Run the one-line command above in PowerShell and enter your student ID and password.
2. **Done:** From here on the script runs by itself in the background and its icon sits next to the clock (green = connected, red = offline) — it logs back in whenever the internet drops, and it starts with Windows.
3. **Settings:** Whenever you want to change something, open cmd and type `autologin` — the panel opens (startup, language, password, check interval, and more).
4. **First test:** On university Wi-Fi, run "Diagnose" from the panel (or `python lu_autologin.py --diagnose`) to make sure login works.
5. **If it does not work:** Keep `autologin.log` and `portal_debug.html`; they are what is needed to add the missing login method.

**Note:** The script checks GitHub every few hours and updates itself when a new version is out; to check manually, use "Check for updates" in the panel.
