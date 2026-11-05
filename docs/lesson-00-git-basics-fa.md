# درس ۰ — محیط Python و مبانی Git

## مرور پایان درس

### موضوع درس

راه‌اندازی Python/VS Code و چرخه‌ی پایه‌ی Git: دیدن تغییر، انتخاب تغییر، بررسی آن و ثبت یک snapshot محلی.

### مدل ذهنی Git

تغییر فایل‌ها مستقیم به commit نمی‌رود. سه جای مهم را به خاطر بسپار:

```text
working tree (فایل‌هایی که ویرایش می‌کنی)
        ↓ git add
staging area (تغییرهای انتخاب‌شده برای commit بعدی)
        ↓ git commit
commit (یک snapshot محلی از تغییرها)
```

`git add` چیزی را به GitHub نمی‌فرستد. `git commit` هم فقط تاریخچه‌ی **محلی** را جلو می‌برد؛ برای فرستادن به remote به‌طور جداگانه `git push` لازم است.

### فرمان‌های مهم و کاربردشان

| فرمان/مفهوم | کاربرد |
|---|---|
| `python -m venv .venv` | ساخت محیط مجازی تا packageهای پروژه از نصب سراسری Python جدا بمانند. |
| `git init` | تبدیل پوشه‌ی فعلی به یک مخزن Git محلی. |
| `git status --short` | نمایش خلاصه‌ی وضعیت؛ اگر خروجی خالی باشد، تغییر ثبت‌نشده یا unstaged باقی نمانده است. |
| `?? file.py` | Git هنوز فایل جدید را track نمی‌کند. |
| ` M file.py` | فایل تغییر کرده، اما تغییر هنوز stage نشده است. |
| `A  file.py` | فایل جدید stage شده و آماده‌ی commit است. |
| `M  file.py` | تغییر فایل stage شده است. |
| `git diff` | نمایش تغییرهای working tree که هنوز stage نشده‌اند. |
| `git add file.py` | انتخاب تغییرهای فایل برای commit بعدی؛ هنوز commit یا upload نشده‌اند. |
| `git diff --cached` | نمایش تغییرهایی که در staging area هستند و قرار است commit شوند. |
| `git commit -m "message"` | ثبت snapshot محلی با توضیح کوتاه. |
| `git log -2 --oneline` | نمایش دو commit آخر به‌صورت فشرده. |

### چرا `.gitignore` مهم است؟

در تمرین، `.gitignore` این موارد را نادیده گرفت:

```text
.venv/
__pycache__/
*.py[cod]
.env
```

`.venv` شامل فایل‌های محیط Python است و نباید به‌عنوان source code وارد Git شود. `.env` هم ممکن است کلید یا تنظیم محرمانه داشته باشد، پس نباید commit شود.

### آنچه عملاً انجام دادی

- Python 3.14.8 و محیط مجازی `.venv` آماده شد؛ داخل venv فقط `pip` بود.
- `hello.py` در venv اجرا شد.
- مخزن محلی با `git init` ساخته شد؛ شاخه‌ی محلی آن `master` است، برای این تمرین مشکلی ندارد.
- commit اول: `e6d53fc Add first Python environment check`.
- پس از ویرایش `hello.py`، `git status` و `git diff` تغییر unstaged را نشان دادند؛ بعد با `git add` به staging رفت.
- commit دوم: `b983e2c Update hello script`؛ بعدش `git status --short` خالی بود.
- پیام `\ No newline at end of file` خطای اجرایی نیست؛ فقط نشان می‌دهد متن فایل newline پایانی ندارد.

### خودآزمایی کوتاه

1. اگر `git status --short` برابر ` M hello.py` باشد، تغییر کجاست؟
2. کدام فرمان diff مربوط به staging را نشان می‌دهد؟
3. آیا `git add` یا `git commit` به‌تنهایی چیزی را به GitHub می‌فرستد؟
4. چرا `.venv` را در `.gitignore` گذاشتیم؟

### یادآوری یک هفته‌ی بعد

بدون نگاه‌کردن به جدول، چرخه را از حفظ بگو: تغییر فایل → بررسی → stage → بررسی staged diff → commit.
