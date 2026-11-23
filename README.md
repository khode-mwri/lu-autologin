# ورود خودکار به اینترنت دانشگاه لرستان | Lorestan University Internet Auto-Login

ابزاری سبک به زبان پایتون که ورود به درگاه اینترنت دانشگاه لرستان (`internet.lu.ac.ir`) و زنده نگه‌داشتن نشست را خودکار می‌کند.
A lightweight Python tool that automates login and session keep-alive for Lorestan University's internet gateway (`internet.lu.ac.ir`).

> این فایل دوزبانه است؛ هر بخش اول به فارسی و بعد به انگلیسی آمده است.
> This README is bilingual; each section comes first in Persian, then in English.

## ⚡ نصب سریع | Quick Install

در PowerShell ویندوز این دستور را بزنید:
Open PowerShell on any Windows PC and run:

```powershell
irm https://raw.githubusercontent.com/khode-mwri/lu-autologin/main/install.ps1 | iex
```

یک بار شماره دانشجویی و پسورد را می‌پرسد، همه‌چیز را راه‌اندازی می‌کند، اسکریپت را به استارتاپ ویندوز اضافه می‌کند و در پس‌زمینه شروع به کار می‌کند.
It will ask for your Student ID and Password once, set up everything, add the script to Windows Startup, and start running silently in the background!

حذف کامل در هر زمان:
To completely uninstall anytime:

```powershell
irm https://raw.githubusercontent.com/khode-mwri/lu-autologin/main/uninstall.ps1 | iex
```

---

## پنل تنظیمات — فقط بنویسید `autologin` | Settings panel — just type `autologin`

بعد از نصب، cmd را دوباره باز کنید و بنویسید:
After install, reopen cmd and type:

```
autologin
```

پنلی باز می‌شود که می‌توانید در آن:
A panel opens where you can:

- سرویس را در پس‌زمینه شروع / متوقف کنید — Start / stop the background service
- اجرای خودکار با ویندوز را فعال / غیرفعال کنید — Enable / disable run on Windows startup
- زبان را عوض کنید (فارسی / English) — Switch language (فارسی / English)
- نام کاربری، پسورد، فاصله‌ی بررسی و زمان تمدید را تغییر دهید — Change username, password, check interval, renewal time
- همین حالا لاگین را تست کنید، پورتال را عیب‌یابی کنید و لاگ را ببینید — Test login now, diagnose the portal, view logs

**نکته درباره‌ی نمایش فارسی در ترمینال:** متن فارسی در Windows Terminal راست‌چین و به‌هم‌پیوسته نمایش داده می‌شود. در cmd قدیمی ممکن است حروف جدا یا جابه‌جا دیده شوند؛ در این صورت از Windows Terminal استفاده کنید یا از داخل پنل زبان را به English تغییر دهید.
**Note on Persian text in the terminal:** Persian renders right-aligned and properly shaped in Windows Terminal. In the old cmd console it may look broken; use Windows Terminal or switch the panel to English.

---

## ویژگی‌ها | Highlights

- **ورود مجدد خودکار:** وقتی اتصال قطع می‌شود متوجه می‌شود و دوباره لاگین می‌کند.
  **Automatic reconnection:** Detects when connectivity drops and logs back in.
- **تمدید پیشگیرانه‌ی نشست:** نشست را پیش از مهلت ۲ ساعته‌ی دانشگاه تمدید می‌کند.
  **Proactive session renewal:** Renews the session before the university's 2-hour timeout.
- **لاگین چندروشی:** شکل دقیق پورتال ممکن است فرق کند (CHAP روشن/خاموش، chap-id به‌صورت بایت خام / اکتال / هگز، فرم به صفحه‌ی خودش یا به آدرس دیگری پست شود، HTTP/HTTPS). اسکریپت بررسی می‌کند صفحه دقیقاً چه چیزی دارد و همه‌ی روش‌های ممکن را امتحان می‌کند — CHAP form POST، plain form POST، plain page POST، CHAP page POST، GET login — تا وقتی یکی با یک بررسی واقعی اینترنت **تأیید** شود. روش برنده در `config.json` ذخیره می‌شود و دفعه‌ی بعد اول امتحان می‌شود.
  **Multi-strategy login:** The portal's exact shape can vary (CHAP on/off, chap-id as raw byte / octal / hex escape, form posting to the page or to a different URL, HTTP/HTTPS). The script detects what the page actually contains and tries every plausible method — CHAP form POST, plain form POST, plain page POST, CHAP page POST, GET login — until one is **verified** by a real internet check. The winning method is remembered in `config.json` and tried first next time.
- **اجرای پس‌زمینه:** بدون اینکه پنجره‌ی ترمینالی باز بماند کار می‌کند.
  **Background execution:** Operates without keeping any terminal windows open.
- **مستقل از مرورگر:** مستقیم با نقطه‌ی ورود لاگین کار می‌کند و به مرورگر نیازی ندارد.
  **Browser-independent:** Directly interacts with the login endpoint without requiring a browser.
- **یکپارچه با استارتاپ ویندوز:** با روشن شدن سیستم، بی‌صدا اجرا می‌شود.
  **Windows Startup integration:** Launches silently on boot.

## اگر لاگین کار نکرد | If login does not work

یک بار روی وای‌فای دانشگاه حالت عیب‌یابی را اجرا کنید — پورتال را می‌گیرد، فرم‌ها و داده‌های CHAP پیدا شده را چاپ می‌کند و صفحه را در `portal_debug.html` ذخیره می‌کند:
Run the diagnose mode once while on university Wi-Fi — it fetches the portal, prints the forms and CHAP data it found, and saves the page to `portal_debug.html`:

```powershell
python lu_autologin.py --diagnose
```

حالت‌های مفید دیگر:
Other useful modes:

```powershell
python lu_autologin.py --once                        # یک بار امتحان کن، بعد خارج شو / try once, then exit
python lu_autologin.py --once --strategy chap-form   # فقط یک روش را امتحان کن / force one method
```

اگر همه‌ی روش‌ها شکست خوردند، لاگ (`autologin.log`) و `portal_debug.html` دقیقاً نشان می‌دهند پورتال چه چیزی برگردانده — همان چیزی که برای اضافه کردن روشِ جاافتاده لازم است. یک مجموعه تست (`tests/`) همه‌ی روش‌های لاگین را روی یک پورتال میکروتیک ساختگی بررسی می‌کند؛ با `python tests/run_strategy_tests.py` اجرا می‌شود.
If every method fails, the log (`autologin.log`) and `portal_debug.html` show exactly what the portal returned — that is what is needed to add the missing method. A test suite (`tests/`) verifies all login methods against a mock MikroTik portal; run it with `python tests/run_strategy_tests.py`.

## اسکریپت‌های دستی | Manual usage scripts

بعد از نصب در `$HOME\LU_AutoLogin` قرار دارند:
Located in `$HOME\LU_AutoLogin` after install:

- `autologin.bat`: باز کردن پنل تنظیمات تعاملی (دستور `autologin`) — Opens the interactive settings panel (`autologin` command).
- `run.bat`: اجرای اسکریپت با لاگ‌های قابل‌مشاهده در پنجره‌ی کنسول — Runs the script with visible logs in a console window.
- `run_background.bat`: اجرای بی‌صدای اسکریپت در پس‌زمینه — Runs the script silently in the background.
- `stop_background.bat`: توقف نمونه‌های در حال اجرای پس‌زمینه — Stops running background instances.
- `enable_startup.bat`: ثبت اسکریپت پس‌زمینه برای اجرا هنگام ورود به ویندوز — Registers the background script to start on Windows logon.
- `disable_startup.bat`: حذف اسکریپت از استارتاپ ویندوز — Removes the script from Windows startup.
- `view_logs.bat`: باز کردن `autologin.log` برای بررسی تاریخچه‌ی اتصال — Opens `autologin.log` to review connection history.

## پیکربندی | Configuration

نام کاربری و تنظیمات به‌صورت محلی در `config.json` ذخیره می‌شوند:
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

*توجه: `config.json` برای محافظت از اطلاعات شخصی کاملاً از گیت نادیده گرفته می‌شود. اسکریپت روش لاگینی که جواب داده (`"strategy"`) و زبان پنل (`"language"`) را هم در `config.json` ذخیره می‌کند و دفعه‌ی بعد اول همان روش را امتحان می‌کند.*
*Note: `config.json` is strictly ignored by git to protect personal credentials. The script also remembers the login method that worked (`"strategy"`) and the panel language (`"language"`) in `config.json`, and tries the winning method first next time.*
