# درس ۳ — خطاهای HTTP و شبکه

## هدف

درخواست API ممکن است موفق شود، سرور ممکن است خطای HTTP بدهد، یا اصلاً ارتباط برقرار نشود. می‌خواهیم این حالت‌ها را از هم تشخیص دهیم تا برنامه (و بعداً Agent) به‌اشتباه با خطا مثل پاسخ موفق رفتار نکند.

## تفاوت خطاها

- **HTTP error**: از سرور پاسخ گرفته‌ایم، ولی درخواست مشکل دارد یا پذیرفته نشده؛ نمونه‌ها: `401` دسترسی لازم است، `403` مجاز نیست، `404` منبع پیدا نشد، `429` درخواست‌های بیش از حد، `5xx` خطای سمت سرور.
- **Network/URL error**: پاسخ HTTP قابل‌استفاده‌ای نگرفته‌ایم؛ مثل قطع اینترنت، DNS یا timeout.
- `HTTPError` از `URLError` ارث می‌برد؛ برای دیدن کد 404 و جزئیاتش، باید `HTTPError` را **زودتر** بگیریم.

## کد کاملِ قابل اجرا

در `api_lesson.py` این نسخه را بگذار. اول URL موفق را اجرا می‌کنیم:

```python
import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

url = "https://jsonplaceholder.typicode.com/todos?userId=2"

try:
    with urlopen(url, timeout=10) as response:
        status = response.status
        body = response.read().decode("utf-8")

except HTTPError as error:
    print("HTTP error:", error.code, error.reason)

except URLError as error:
    print("Network or URL error:", error.reason)

else:
    print("HTTP status:", status)
    data = json.loads(body)
    print("Number of records:", len(data))
```

در ترمینال VS Code اجرا کن:

```powershell
.\.venv\Scripts\python.exe .\api_lesson.py
```

برای URL اصلی انتظار داریم `HTTP status: 200` و تعداد رکوردها را ببینی.

## توضیح کد، بخش‌به‌بخش

1. `import json` ابزار تبدیل متن JSON را وارد می‌کند.
2. `HTTPError` و `URLError` دو دسته‌ی خطایی‌اند که در درخواست وب ممکن است بگیریم.
3. `urlopen(url, timeout=10)` درخواست GET را می‌فرستد و برای عملیات شبکه حداکثر ۱۰ ثانیه منتظر می‌ماند.
4. داخل `try` کدی است که ممکن است خطا بدهد. اگر پاسخ موفق برسد، status و متن body را ذخیره می‌کنیم.
5. `except HTTPError` پاسخ‌های HTTP مثل 404 را جداگانه می‌گیرد؛ `error.code` کد و `error.reason` توضیح کوتاه است.
6. `except URLError` مشکلات اتصال، URL یا DNS را می‌گیرد. چون `HTTPError` زیرمجموعه‌ی آن است، باید قبل از آن catch شود.
7. `else` فقط وقتی اجرا می‌شود که بلوک `try` بدون exception تمام شده باشد؛ بنابراین فقط آن‌جا body را به JSON تبدیل می‌کنیم.
8. `len(data)` تعداد آیتم‌های فهرست را می‌شمارد.

## آزمایش 404

پس از دیدن پاسخ موفق، فقط URL را به این مقدار تغییر بده و دوباره اجرا کن:

```python
url = "https://httpbin.org/status/404"
```

این‌بار انتظار داریم شاخه‌ی `HTTPError` کد `404` را چاپ کند. اگر شبکه‌ات به httpbin دسترسی ندارد، همان متن خطا را بفرست؛ نتیجه‌ی ناموفق هم بخشی از یادگیری است.

### چرا `timeout=10` ده ثانیه صبر نکرد؟

`timeout=10` **مکث اجباری نیست**؛ فقط حد انتظار برای عملیات شبکه را محدود می‌کند. در آزمایش بالا سرور خیلی زود پاسخ HTTP با کد 404 فرستاد، پس `urlopen` همان لحظه `HTTPError` را بالا برد. چون پاسخی دریافت شده بود، دلیلی برای منتظرماندن تا ۱۰ ثانیه نبود. Timeout زمانی مهم می‌شود که اتصال یا دریافت داده بیش از حد منتظر بماند.

## نکته‌ی مهم برای Agentها

Retry را کورکورانه و بی‌نهایت انجام نمی‌دهیم. نوع خطا را تشخیص می‌دهیم، برای timeout و rate limit سیاست محدود می‌گذاریم، و قبل از ادامه مطمئن می‌شویم خروجی ابزار واقعاً معتبر است.

## مرور پایان درس ۳

### موضوع و مدل ذهنی

درخواست API ممکن است به سه شکل پیش برود:

1. سرور پاسخ موفق بدهد؛ وارد `else` می‌شویم و پاسخ را پردازش می‌کنیم.
2. سرور پاسخ HTTP ناموفق مثل 404 بدهد؛ `HTTPError` را می‌گیریم.
3. ارتباط/URL مشکل داشته باشد؛ `URLError` را می‌گیریم.

`timeout=10` مکث اجباری نیست؛ حد انتظار برای عملیات شبکه است. اگر پاسخ 404 سریع برسد، برنامه همان موقع خطا را گزارش می‌کند.

### ساختارها و دستورهای مهم

| کد/ساختار | چه می‌کند؟ |
|---|---|
| `try` | بخشی را اجرا می‌کند که ممکن است exception بدهد. |
| `except HTTPError as error` | خطاهای HTTP را می‌گیرد؛ `error.code` و `error.reason` جزئیاتش هستند. |
| `except URLError as error` | خطای URL/شبکه را می‌گیرد؛ `error.reason` علت را نشان می‌دهد. |
| ترتیب HTTPError سپس URLError | مهم است چون `HTTPError` زیرمجموعه‌ی `URLError` است. |
| `else` | فقط وقتی اجرا می‌شود که در `try` هیچ exception رخ نداده باشد. |
| `timeout=10` | انتظار عملیات شبکه را محدود می‌کند؛ برنامه را ده ثانیه نگه نمی‌دارد. |
| `json.loads(body)` | body موفق را از متن JSON به ساختارهای Python تبدیل می‌کند. |
| `len(data)` | تعداد رکوردهای فهرست را می‌دهد. |
| `\.venv\Scripts\python.exe .\api_lesson.py` | فایل را با Python محیط مجازی پروژه اجرا می‌کند. |

### خروجی‌هایی که تو گرفتی

- `https://httpbin.org/status/404` → `HTTP error: 404 NOT FOUND`؛ پس شاخه‌ی `HTTPError` درست کار کرد.
- `https://jsonplaceholder.typicode.com/todos?userId=2` → status برابر 200 و اجرای شاخه‌ی `else`؛ فهرست رکوردها پردازش شد.

### خطاهای رایج

- گرفتن `URLError` قبل از `HTTPError` و از دست‌دادن رسیدگی ویژه به statusهای HTTP.
- تصور این‌که timeout مکث اجباری است یا پاسخ 404 یعنی اینترنت قطع شده.
- تلاش برای parse کردن body در شاخه‌ی خطا، قبل از این‌که موفقیت درخواست تأیید شده باشد.

### خودآزمایی

1. چرا `HTTPError` را قبل از `URLError` می‌گیریم؟
2. پاسخ HTTP با کد 404 چه فرقی با قطع اتصال دارد؟
3. اگر بلوک `try` بدون exception تمام شود، کدام بخش اجرا می‌شود؟
4. آیا `timeout=10` یعنی برنامه همیشه ده ثانیه صبر می‌کند؟

**پاسخ تو به سؤال اول درست بود:** `HTTPError` زیرمجموعه‌ی `URLError` است؛ اگر اول `URLError` را بگیریم، خطای 404 هم همان‌جا گرفته می‌شود و handler ویژه‌ی `HTTPError` اجرا نخواهد شد.
