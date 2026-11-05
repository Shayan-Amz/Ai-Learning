# درس ۱ — اولین API با Python

## هدف این درس

در پایان بتوانی یک درخواست ساده بفرستی، کد وضعیت پاسخ را بخوانی و JSON را به داده‌ی Python تبدیل کنی. برای این تمرین **هیچ package یا API key لازم نیست**؛ از کتابخانه‌های خود Python استفاده می‌کنیم.

## API خیلی خلاصه

API یک قرارداد برای ارتباط بین دو برنامه است. برنامه‌ی ما (client) یک request به سرویس (server) می‌فرستد؛ سرویس response برمی‌گرداند. در این تمرین:

- `GET` می‌گوید «این داده را برایم بخوان»؛
- `/todos/1` آدرس یک رکورد آزمایشی است؛
- `200` یعنی درخواست موفق بوده؛
- JSON داده‌ی ساخت‌یافته‌ای است که به شکل object/list در Python قابل استفاده می‌شود.

## اجرا

در پوشه‌ی `C:\Users\shaya\ai-learning-practice`، در VS Code یک فایل به نام `api_lesson.py` بساز و این کد را داخلش بگذار:

```python
import json
from urllib.request import urlopen

url = "https://jsonplaceholder.typicode.com/todos/1"

with urlopen(url, timeout=10) as response:
    print("HTTP status:", response.status)
    body = response.read().decode("utf-8")

todo = json.loads(body)

print("Title:", todo["title"])
print("Completed:", todo["completed"])
print("Whole object:", todo)
```

در PowerShell داخلی VS Code اجرا کن:

```powershell
.\.venv\Scripts\python.exe .\api_lesson.py
```

خروجی معمولاً با `HTTP status: 200` شروع می‌شود. عنوان نمونه ممکن است `delectus aut autem` باشد و `Completed` مقدار `False` داشته باشد. این endpoint فقط داده‌ی آزمایشی عمومی برمی‌گرداند.

## کد چه می‌کند؟

1. `urlopen` یک درخواست GET می‌فرستد؛ `timeout=10` نمی‌گذارد برنامه بی‌نهایت منتظر بماند.
2. `response.status` کد HTTP را می‌دهد.
3. `response.read()` متن پاسخ را می‌خواند؛ `decode("utf-8")` بایت‌ها را به متن تبدیل می‌کند.
4. `json.loads(body)` متن JSON را به یک dictionary در Python تبدیل می‌کند.
5. `todo["title"]` و `todo["completed"]` دو فیلد را از آن dictionary می‌خوانند.

### بررسی پاسخ تو

برداشتت درست بود: فراخوانی `urlopen(url, timeout=10)` درخواست را می‌فرستد؛ `body` متن JSON پس از تبدیل بایت‌ها به متن است؛ و `json.loads(body)` آن متن را به دیکشنری Python به نام `todo` تبدیل می‌کند. ظرافتش این است که `urlopen(...)` درخواست را می‌فرستد، ولی `with` مسئول مدیریت پاسخ و بستن آن در پایان بلوک است. `200` هم موفقیت در سطح HTTP را نشان می‌دهد؛ هنوز باید خود داده و فیلدهای موردنیاز را بررسی کنیم.

## تمرین

در URL عدد آخر را از `1` به `2` تغییر بده، فایل را ذخیره و دوباره اجرا کن. عنوان را مقایسه کن. سپس با زبان خودت جواب بده:

- کدام خط request را می‌فرستد؟
- اگر `status` برابر 200 نباشد، چه چیزی باید بررسی کنیم؟
- فرق `body` با `todo` چیست؟

اگر خطای شبکه دیدی، متن کامل خطا را بفرست؛ هیچ کلید یا اطلاعات شخصی در این API آزمایشی وارد نکن.

## مرور پایان درس ۱

### موضوع و مدل ذهنی

یک برنامه به‌عنوان client درخواست GET می‌فرستد، سرویس با status و body پاسخ می‌دهد، و ما body را از JSON به داده‌ی Python تبدیل می‌کنیم:

```text
GET → HTTP response (status + body) → bytes → str → JSON parser → Python dict
```

### کدها و دستورهای مهم

| کد/دستور | چه می‌کند؟ |
|---|---|
| `urlopen(url, timeout=10)` | درخواست GET را می‌فرستد و حداکثر ۱۰ ثانیه برای پاسخ صبر می‌کند. |
| `with ... as response` | منبع پاسخ را مدیریت می‌کند و بعد از بلوک می‌بندد. خود درخواست را `urlopen(...)` می‌فرستد. |
| `response.status` | کد وضعیت HTTP را می‌خواند؛ `200` موفقیت HTTP است، نه تضمینِ درست‌بودن معنای داده. |
| `response.read()` | body را به شکل bytes می‌خواند. |
| `.decode("utf-8")` | bytes را به متن `str` تبدیل می‌کند. |
| `json.loads(body)` | متن JSON را به داده‌ی Python تبدیل می‌کند؛ در پاسخ تکی با `{...}` نتیجه `dict` است. |
| `todo["title"]` | مقدار فیلد `title` را از dictionary می‌خواند. |
| `type(value).__name__` | نام نوع Python را برای بررسی نشان می‌دهد؛ اینجا `str` و `dict`. |

### نتیجه‌ای که خودت دیدی

برای `/todos/2`، status برابر 200 بود؛ `body` از نوع `str` و `todo` از نوع `dict` بود. پاسخ شامل `id=2` و یک مقدار boolean برای `completed` بود.

### خودآزمایی

1. `urlopen(...)` چه چیزی می‌فرستد و `with` چه مسئولیتی دارد؟
2. چرا `json.loads(body)` لازم است؟
3. آیا status 200 به‌تنهایی ثابت می‌کند پاسخ از نظر محتوا درست است؟ چرا؟
